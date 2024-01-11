import asyncio
import base64
import datetime
from collections import defaultdict
from datetime import datetime, timedelta

import pyrogram
import websockets
from pyrogram.raw import functions
from pyrogram.raw.base import StatsGraph
from pyrogram.raw.functions.contacts import ResolveUsername
from pyrogram.raw.functions.stats import LoadAsyncGraph
from pyrogram.raw.types import InputChannel, StatsGraphAsync
from Handlers.menu_handlers import bytes_to_base64
from api import *
from bot import bot
from bot import bot_token
from bot import pyro_client

queue = asyncio.Queue()


async def get_access_hash(client, channel_id):
    try:
        # Get channel information by ID
        channel = await client.get_chat(channel_id)
        channel_username = channel.username

        if channel_username is None:
            raise ValueError("Channel username not found.")

        # Resolve the username to get access_hash
        result = await client.invoke(ResolveUsername(username=channel_username))

        # Extract channel_id and access_hash from the response
        if result.peer and hasattr(result.peer, 'channel_id'):
            channel_id = result.peer.channel_id
            # Find the matching channel in the chats list to get the access_hash
            for chat in result.chats:
                if chat.id == channel_id:
                    return chat.id, chat.access_hash

        return None, None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None

def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')

def process_graph_data(graph):
    dates = [timestamp_to_date(x) for x in graph['columns'][0][1:]]  # Convert timestamps
    series_data = {}

    for series_index, series_name in enumerate(graph['names'], start=1):
        series_values = graph['columns'][series_index][1:]
        series_data[graph['names'][series_name]] = dict(zip(dates, series_values))

    return series_data


async def fetch_async_graph_data(client, token):
    try:
        # Invoke LoadAsyncGraph with the provided token
        result = await client.invoke(LoadAsyncGraph(token=token, x=0))  # Adjust 'x' as needed

        # Check if the result is a StatsGraph object
        if isinstance(result, pyrogram.raw.types.stats_graph.StatsGraph):
            # If result contains JSON data, parse it
            if hasattr(result, 'json') and result.json:
                graph_data = json.loads(result.json.data)
                return graph_data
            else:
                print("StatsGraph object received but does not contain valid JSON data.")
                return None
        else:
            print(f"Unexpected response type: {type(result)}")
            return None
    except Exception as e:
        print(f"Error fetching async graph data: {e}")
        return None


async def get_broadcast_stats(channel_username):
    try:
        # Get channel_id and access_hash
        channel_id, access_hash = await get_access_hash(pyro_client, channel_username)
        if channel_id is None or access_hash is None:
            raise ValueError("Unable to resolve channel username to ID and access hash")

        # Create InputChannel
        input_channel = InputChannel(channel_id=channel_id, access_hash=access_hash)

        # Fetch broadcast stats using Pyrogram's raw API
        broadcast_stats = await pyro_client.invoke(functions.stats.GetBroadcastStats(channel=input_channel))

        # Process the BroadcastStats object
        processed_stats = {
            'period': {
                'min_date': timestamp_to_date(broadcast_stats.period.min_date),
                'max_date': timestamp_to_date(broadcast_stats.period.max_date)
            },
            'followers': {
                'current': broadcast_stats.followers.current,
                'previous': broadcast_stats.followers.previous
            },
            'views_per_post': {
                'current': broadcast_stats.views_per_post.current,
                'previous': broadcast_stats.views_per_post.previous
            },
            'shares_per_post': {
                'current': broadcast_stats.shares_per_post.current,
                'previous': broadcast_stats.shares_per_post.previous
            },
            'enabled_notifications': {
                'part': broadcast_stats.enabled_notifications.part,
                'total': broadcast_stats.enabled_notifications.total
            }
        }

        # Process StatsGraph and StatsGraphAsync fields
        graph_fields = ['growth_graph', 'followers_graph', 'mute_graph', 'top_hours_graph',
                        'interactions_graph', 'iv_interactions_graph', 'views_by_source_graph',
                        'new_followers_by_source_graph', 'languages_graph']

        # Process each graph field
        for field in graph_fields:
            graph = getattr(broadcast_stats, field, None)
            if isinstance(graph, StatsGraph):
                graph_data = json.loads(graph.json.data)
                processed_stats[field] = process_graph_data(graph_data)
            elif isinstance(graph, StatsGraphAsync):
                async_graph_data = await fetch_async_graph_data(pyro_client, graph.token)
                if async_graph_data:
                    processed_stats[field] = process_graph_data(async_graph_data)

        print(processed_stats)
        return processed_stats

    except Exception as e:
        print(f"An error occurred: {e}")
        return None



async def get_messages_from_past_days(chat_id, number_of_days, start_date=None, max_retries=2):
    # if start_date is None:
    #     # Set start_date to be 3 days before now for testing
    #     start_date = (datetime.utcnow() - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)

    logging.info(f"Starting to fetch messages from past {number_of_days} days for channel {chat_id}.")
    days_ago = (datetime.utcnow() - timedelta(days=number_of_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    all_messages = []
    attempt = 0
    yield_object = pyro_client.get_chat_history(
        chat_id, offset_date=start_date) if start_date else pyro_client.get_chat_history(chat_id)

    while True:
        try:
            # Using offset_date if start_date is provided
            async for message in yield_object:
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


async def get_daily_views_by_channel(channel_name, number_of_days, offset_date=None):
    try:
        chat = await pyro_client.get_chat(channel_name)
        chat_id = chat.id

        # Pass the offset_date to the get_messages_from_past_days function
        messages = await get_messages_from_past_days(chat_id, number_of_days, start_date=offset_date)
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


async def get_messages_from_past_year(chat_id, max_retries=2, delay_between_batches=5):
    logging.info(f"Starting to fetch messages from past year for channel {chat_id}.")
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    all_messages = []
    first_batch = True
    batch_count = 0

    while start_date < end_date:
        batch_count += 1
        logging.info(f"Batch {batch_count}: Processing batch starting from {start_date}.")

        # Calculate the end of the month for the current start_date
        if first_batch:
            batch_end_date = end_date
            first_batch = False
        elif start_date.month == 12:
            batch_end_date = datetime(start_date.year + 1, 1, 1)
        else:
            batch_end_date = datetime(start_date.year, start_date.month + 1, 1)
        batch_end_date = min(batch_end_date, end_date)

        logging.info(f"Batch {batch_count}: Fetching messages from {start_date} to {batch_end_date}.")

        attempt = 0
        while attempt < max_retries:
            try:
                yield_object = pyro_client.get_chat_history(chat_id, offset_date=start_date, limit=None)
                message_count = 0

                async for message in yield_object:
                    if message.date >= batch_end_date:
                        break
                    all_messages.append(message)
                    message_count += 1

                logging.info(
                    f"Batch {batch_count}: Fetched {message_count} messages. Total messages so far: {len(all_messages)}")

                start_date = batch_end_date
                break  # Exit the retry loop on success

            except asyncio.TimeoutError:
                attempt += 1
                wait_time = 2 ** attempt  # Exponential backoff
                logging.warning(
                    f"Batch {batch_count}: Timeout occurred. Retrying in {wait_time} seconds. Attempt {attempt}/{max_retries}.")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logging.error(f"Batch {batch_count}: Error while fetching or processing messages: {e}")
                break  # Exit on other exceptions

        logging.info(
            f"Batch {batch_count}: Completed fetching. Waiting {delay_between_batches} seconds before next batch.")
        await asyncio.sleep(delay_between_batches)

    logging.info(f"Finished fetching messages for channel {chat_id}. Total messages fetched: {len(all_messages)}")
    return all_messages


async def calculate_monthly_views(messages):
    monthly_views = defaultdict(lambda: {"views": 0, "last_message_id": None})
    for message in messages:
        if hasattr(message, 'views') and message.views and message.date:
            # Format the month as 'YYYY-MM'
            message_month = message.date.strftime('%Y-%m')
            view_count = message.views
            monthly_views[message_month]["views"] += view_count
            monthly_views[message_month]["last_message_id"] = message.id
    return monthly_views


async def get_monthly_views_by_channel(chat_id):
    try:
        chat = await pyro_client.get_chat(chat_id)
        chat_id = chat.id

        # Fetch messages from the past year
        messages = await get_messages_from_past_year(chat_id)
        views_by_month = await calculate_monthly_views(messages)

        # Creating a list of dictionaries for each month
        monthly_stats = [
            {"month": month, "views": data["views"], "lastMessageId": data["last_message_id"]}
            for month, data in views_by_month.items()
        ]

        # Serialize the list of dictionaries to a JSON formatted string
        return json.dumps(monthly_stats)

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
                    "get_subscribers_count_batch": get_subscribers_count_batch,
                    "getMessagesFromPastYear": get_monthly_views_by_channel,
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
    workers = []

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
