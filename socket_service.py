import json
import traceback

import websockets
import asyncio
import datetime
from collections import defaultdict
from datetime import datetime, timedelta

from Handlers.menu_handlers import bytes_to_base64
from bot import bot
import websockets

from api import *
from bot import pyro_client
from bot import Bot, bot_token
import base64

queue = asyncio.Queue()


async def get_messages_from_past_days(chat_id, number_of_days, max_retries=2):
    logging.info(f"Starting to fetch messages from past {number_of_days} days for channel {chat_id}.")
    days_ago = (datetime.utcnow() - timedelta(days=number_of_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    all_messages = []
    attempt = 0

    while True:
        try:
            async for message in pyro_client.get_chat_history(chat_id):
                if message.date < days_ago:
                    logging.debug(
                        f"Message {message.id} is older than the specified days: {message.date} < {days_ago}")
                    return all_messages
                all_messages.append(message)
                logging.debug(f"Appended message {message.id} from {message.date}")

        except asyncio.TimeoutError:
            if attempt < max_retries:
                attempt += 1
                wait_time = 1  # Exponential backoff
                logging.warning(f"Timeout occurred. Retrying in {wait_time} seconds. Attempt {attempt}/{max_retries}.")
                await asyncio.sleep(wait_time)
                continue  # Retry the request
            else:
                logging.error("Max retries reached. Giving up.")
                break
        except Exception as e:
            logging.error(f"Error while fetching or processing messages: {e}")
            break

    return all_messages


async def calculate_daily_views(messages):
    daily_views = defaultdict(lambda: {"views": 0, "last_message_id": None})
    for message in messages:
        if hasattr(message, 'views') and message.views and message.date:
            # Ensure message.date is used as a datetime object throughout
            message_date = message.date.date()  # Extracting only the date part
            view_count = message.views
            daily_views[message_date.isoformat()]["views"] += view_count
            daily_views[message_date.isoformat()]["last_message_id"] = message.id
    return daily_views


async def get_daily_views_by_channel(channel_name, number_of_days):
    try:
        chat = await pyro_client.get_chat(channel_name)
        chat_id = chat.id

        messages = await get_messages_from_past_days(chat_id, number_of_days)
        views_by_day = await calculate_daily_views(messages)

        # Creating a list of dictionaries for each day
        daily_stats = [
            {"date": str(day), "views": data["views"], "lastMessageId": data["last_message_id"]}
            for day, data in views_by_day.items()
        ]

        # Serialize the list of dictionaries to a JSON formatted string
        return json.dumps(daily_stats)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Return a JSON formatted empty list
        return json.dumps([])


async def getStat(channelName: str):
    async for message in pyro_client.get_chat_history(channelName):
        print(message)


async def get_subscribers_count(channel_id):
    count = await pyro_client.get_chat_members_count(channel_id)
    return count


async def get_subscribers_count_batch(channel_ids: List[int], batch_size: int = 100):
    semaphore = asyncio.Semaphore(10)

    async def get_count(channel_name):
        async with semaphore:
            try:
                count = await pyro_client.get_chat_members_count(channel_name)
            except Exception as e:
                print(f"Error fetching data for {channel_name}: {e}")
                count = 0  # Set count to 0 in case of error
            return channel_name, count

    batches = [channel_ids[i:i + batch_size] for i in range(0, len(channel_ids), batch_size)]
    counts = {}
    for batch in batches:
        tasks = [get_count(channel) for channel in batch]
        results = await asyncio.gather(*tasks)
        counts.update({channel_name: count for channel_name, count in results})

    return json.dumps(counts)


async def get_profile_picture_and_username(user_id):
    print(f"userid = {user_id}")
    try:
        avatar_bytes = None  # Default to None in case no profile photo is found
        profile_photos = await bot.get_user_profile_photos(user_id, limit=1)

        if profile_photos.photos:
            # Choose a larger size for the profile photo if available
            photo = profile_photos.photos[0][0]
            file = await bot.get_file(photo.file_id)
            file_path = file.file_path
            url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        avatar_bytes = await response.read()  # byte array of the photo

        # Convert bytes to base64 string
        avatar_base64 = base64.b64encode(avatar_bytes).decode('utf-8') if avatar_bytes else None

        # Get user info
        user_data = await pyro_client.get_users(user_id)
        username = user_data.first_name  # or user_data.username based on what you want

        return json.dumps({'avatar': avatar_base64, 'username': username})

    except Exception as e:
        print(f"Exception in get_profile_picture_and_username occurred: {e}")
        return json.dumps({'error': str(e)})


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
                    "get_subscribers_count_batch": get_subscribers_count_batch
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


async def connectToHub():
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

            except TypeError as e:
                result_message = {"invocationId": invocation_id, "error": f"Invalid parameters for function: {str(e)}"}
            except Exception as e:
                result_message = {"invocationId": invocation_id, "error": f"Error in function execution: {str(e)}"}

            finally:
                # Send the result back
                start_message = {
                    "type": 1,
                    "invocationId": "invocation_id",
                    "target": "ReceiveStream",
                    "arguments": [
                        'Bebra'
                    ],
                    "streamIds": [
                        "stream_id"
                    ]
                }
                await websocket.send(toSignalRMessage(start_message))
                print(result_message)
                json_result = json.dumps(result_message)

                message = {
                    "type": 2,
                    "invocationId": "stream_id",
                    "item": f'{json_result}'
                }
                await websocket.send(toSignalRMessage(message))

                completion_message = {
                    "type": 3,
                    "invocationId": "stream_id"
                }
                await websocket.send(toSignalRMessage(completion_message))
                queue.task_done()


    connection_closed_printed = False

    while True:
        try:
            # Use BASE_URL for negotiation endpoint
            negotiation = requests.post(f'{BASE_URL}/BotHub/negotiate?negotiateVersion=0').json()
            connectionid = negotiation['connectionId']
            # Use BASE_URL to form the WebSocket URI
            ws_scheme = 'wss' if BASE_URL.startswith('https') else 'ws'
            uri = f"{ws_scheme}://{BASE_URL.split('://')[1]}/BotHub?id={connectionid}"
            # print(uri)
            async with websockets.connect(uri) as websocket:
                await handshake(websocket)
                running = True
                workers = [asyncio.create_task(worker(queue, websocket)) for _ in range(1)]
                listen_task = asyncio.create_task(listen(websocket, running))
                ping_task = asyncio.create_task(start_pinging(websocket, running))
                connection_closed_printed = False

                await asyncio.gather(listen_task, ping_task)
        except Exception as e:
            for worker in workers:
                worker.cancel()
            if not connection_closed_printed:
                print(f"Error: {e}")
                print("Connection closed")
                print("Looking for connection...")
                connection_closed_printed = True
            await asyncio.sleep(5)
