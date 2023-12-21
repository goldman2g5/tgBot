import json

import websockets
import asyncio
import datetime
from collections import defaultdict
from datetime import datetime, timedelta
from bot import bot
import websockets

from api import *
from bot import client, pyro_client
from bot import Bot


# Function for summing two numbers
def sum_of_two(number1, number2):
    print("function call")
    try:
        num1 = float(number1)
        num2 = float(number2)
    except ValueError:
        return {"error": "Invalid input. Please provide valid numbers."}

    total = num1 + num2
    return {"result": [total, 228], "bebra": {"zieg": "hail"}, "status": {"trezvost": False}}


async def get_messages_from_past_days(channel_id, number_of_days):
    days_ago = datetime.now() - timedelta(days=number_of_days)
    all_messages = []
    from_message_id = 0

    while True:
        messages = await client.api.get_chat_history(
            channel_id,
            from_message_id=from_message_id,
            offset=0,
            limit=1,
            only_local=False,
        )

        if not messages.messages:
            break

        for message in messages.messages:
            message_date = datetime.utcfromtimestamp(message.date)
            if message_date < days_ago:
                return all_messages
            all_messages.append(message)

        from_message_id = messages.messages[-1].id

    return all_messages


def remove_negative_100(n: int) -> int:
    s = str(n)
    prefix = "-100"
    if s.startswith(prefix):
        return int(s[len(prefix):])
    return n


async def calculate_daily_views(messages):
    daily_views = defaultdict(lambda: {"views": 0, "last_message_id": None})
    for message in messages:
        if message.interaction_info.view_count is not None and message.date is not None:
            message_date = datetime.utcfromtimestamp(message.date).date()
            view_count = message.interaction_info.view_count
            daily_views[message_date.isoformat()]["views"] += view_count
            daily_views[message_date.isoformat()]["last_message_id"] = message.id
    return daily_views


async def get_daily_views_by_channel(channel_name, number_of_days):
    try:
        chat = await bot.get_chat(channel_name)
        chatid = chat.id
        # print(f"Chat ID: {chatid}")

        messages = await get_messages_from_past_days(chatid, number_of_days)
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
    resp = pyro_client.get_chat_history(channelName)


async def get_subscribers_count(channel_name: str):
    count = await pyro_client.get_chat_members_count(channel_name)
    return count


async def get_profile_picture_and_username(user_id: int):
    print(user_id)
    pfp = await bot.get_user_profile_photos(user_id, limit=1)
    username = await pyro_client.get_users(user_id)['username']
    return {'profile_picture': pfp[0], 'username': username}


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
            # print(f"get_response: {get_response}")
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
                    "sumOfTwo": sum_of_two,
                    "getDailyViewsByChannel": get_daily_views_by_channel,
                    "getSubscribersCount": get_subscribers_count
                }

                if function_name in function_map:
                    try:
                        if asyncio.iscoroutinefunction(function_map[function_name]):
                            result = await async_wrapper(function_map[function_name], **parameters)
                        else:
                            result = function_map[function_name](**parameters)
                        result = {"invocationId": invocation_id, "data": result}
                    except TypeError as e:
                        result = {"invocationId": invocation_id,
                                  "error": f"Invalid parameters for {function_name}: {str(e)}"}
                    except Exception as e:
                        result = {"invocationId": invocation_id, "error": f"Error in {function_name}: {str(e)}"}
                else:
                    result = {"invocationId": invocation_id, "error": "Unknown function"}
            else:
                # print("Not a function call type message. Skipping.")

                continue

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
            # print(result)
            json_result = json.dumps(result)

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
        except websockets.exceptions.ConnectionClosed:
            break


async def connectToHub():
    print("Connecting to hub...")
    while True:
        try:
            negotiation = requests.post('http://localhost:7256/BotHub/negotiate?negotiateVersion=0').json()
            connectionid = negotiation['connectionId']
            uri = f"ws://localhost:7256/BotHub?id={connectionid}"
            async with websockets.connect(uri) as websocket:
                await handshake(websocket)
                running = True
                listen_task = asyncio.create_task(listen(websocket, running))
                ping_task = asyncio.create_task(start_pinging(websocket, running))

                await asyncio.gather(listen_task, ping_task)
        except Exception as e:
            print(f"Error: {e}")
            print("Connection closed, attempting to reconnect...")
            await asyncio.sleep(5)
