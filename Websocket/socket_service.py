import uuid

from Websocket.SocketFunctions import *

queue = asyncio.Queue()


def toSignalRMessage(data):
    return f'{json.dumps(data)}\u001e'


async def async_wrapper(func, **params):
    return await func(**params)


async def handshake(websocket):
    await websocket.send(toSignalRMessage({"protocol": "json", "version": 1}))
    handshake_response = await websocket.recv()
    print(f"handshake_response: {handshake_response}")


async def start_pinging(websocket, running):
    while running:
        await asyncio.sleep(10)
        try:
            await websocket.send(toSignalRMessage({"type": 6}))
        except websockets.exceptions.ConnectionClosed:
            break


async def listen(websocket, running):
    while running:
        try:
            get_response = await websocket.recv()
            print(f"get_response: {get_response}")
            end_of_json = get_response.rfind("}") + 1
            json_string = get_response[:end_of_json]

            try:
                outer_message_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                continue

            if "arguments" in outer_message_data and outer_message_data["arguments"]:
                try:
                    function_call_data = json.loads(outer_message_data["arguments"][0])
                except (IndexError, json.JSONDecodeError) as e:
                    print(f"Error processing arguments: {e}")
                    continue

                function_name = function_call_data.get("functionName")
                parameters = function_call_data.get("parameters", {})
                invocation_id = function_call_data.get("invocationId", "unknown")

                function_map = {
                    "getDailyViewsByChannel": get_daily_views_by_channel,
                    "getSubscribersCount": get_subscribers_count,
                    "getProfilePictureAndUsername": get_profile_picture_and_username,
                    "get_subscribers_count_batch": get_subscribers_count_batch,
                    "getMonthlyViews": get_monthly_views_by_channel,
                    "getBroadcastStats": get_broadcast_stats
                }

                if function_name in function_map:
                    # Just enqueue the task with necessary context and let the worker handle execution
                    await queue.put((function_map[function_name], parameters, invocation_id,
                                     asyncio.iscoroutinefunction(function_map[function_name])))
                else:
                    print(f"Unknown function: {function_name}")
            else:
                print("Not a function call type message. Skipping.")

                continue
        except websockets.exceptions.ConnectionClosed:
            break


BASE_URL = API_URL.rsplit('/', 1)[0]
stream_id = None


async def connectToHub():
    global stream_id
    print("Connecting to hub...")

    async def worker(queue, websocket):
        while True:
            func, params, invocation_id, is_coroutine = await queue.get()

            try:
                # Execute the function and handle the result
                if is_coroutine:
                    result = await func(**params)
                else:
                    result = func(**params)

                # Prepare the result message
                result_message = {"invocationId": invocation_id, "data": result}

            except Exception as e:
                # Log the error and send an error response instead
                print(f"Error during task execution: {e}")
                result_message = {"invocationId": invocation_id, "error": str(e)}

            finally:
                # Ensure sending the response
                try:
                    print(result_message)
                    json_result = json.dumps(result_message)

                    message = {
                        "type": 2,
                        "invocationId": f"{stream_id}",
                        "item": f'{json_result}'
                    }
                    await websocket.send(toSignalRMessage(message))
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"WebSocket connection error: {e}")

                queue.task_done()

    workers = []
    listen_task = None
    ping_task = None
    conn_closed_printed = False

    while True:
        try:
            listen_task = None
            ping_task = None
            workers.clear()

            negotiation = requests.post(f'{BASE_URL}/BotHub/negotiate?negotiateVersion=0').json()
            connectionid = negotiation['connectionId']
            ws_scheme = 'wss' if BASE_URL.startswith('https') else 'ws'
            uri = f"{ws_scheme}://{BASE_URL.split('://')[1]}/BotHub?id={connectionid}"

            async with websockets.connect(uri) as websocket:
                await handshake(websocket)

                if stream_id:
                    completion_message = {
                        "type": 3,
                        "invocationId": f"{stream_id}",
                        "streamIds": [f"{stream_id}"]

                    }
                    await websocket.send(toSignalRMessage(completion_message))

                stream_id = str(uuid.uuid4())

                # Send a Type 3 message to close previous stream if any
                # Immediately send a Type 1 message to open a new stream
                start_message = {
                    "type": 1,
                    "invocationId": f"{stream_id}",
                    "target": "ReceiveStream",
                    "arguments": ['Bebra'],
                    "streamIds": [f"{stream_id}"]
                }
                await websocket.send(toSignalRMessage(start_message))

                running = True
                workers = [asyncio.create_task(worker(queue, websocket)) for _ in range(1)]
                listen_task = asyncio.create_task(listen(websocket, running))
                ping_task = asyncio.create_task(start_pinging(websocket, running))

                await asyncio.gather(listen_task, ping_task)
        except Exception as e:
            print(f"Error: {e}")
            if not conn_closed_printed:
                conn_closed_printed = True
                print("Connection closed. Looking for connection...")
            await asyncio.sleep(5)