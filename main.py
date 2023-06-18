import asyncio

from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *
from aiogram.utils import executor
import time
import requests
import json
import redis
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.middlewares import BaseMiddleware

import asyncio
import time
import requests
import json
import redis
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.middlewares import BaseMiddleware

async def check_notifications():
    while True:
        try:
            # Fetch notifications from the API
            response = requests.get('http://localhost:8053/api/Notification')
            response.raise_for_status()  # Raise an exception for non-2xx responses

            notifications = response.json()

            # Process each notification
            for notification in notifications:
                # Extract required information from the notification
                channel_name = notification['channelName']
                send_time = notification['sendTime']
                telegram_user_id = notification['telegramUserId']
                telegram_chat_id = notification['telegramChatId']

                # Send the notification to the user using the bot
                await bot.send_message(telegram_chat_id, f"New notification for {channel_name} at {send_time}")

        except (requests.RequestException, json.JSONDecodeError) as e:
            # Log the error and continue the loop
            print(f"Error fetching notifications: {str(e)}")

        # Wait for 30 minutes before checking for new notifications again
        await asyncio.sleep(30 * 60)

async def background_on_start() -> None:
    """Background task which is created when bot starts"""
    while True:
        await asyncio.sleep(5)
        print("Hello World!")

async def background_on_action() -> None:
    """Background task which is created when the user asked"""
    for _ in range(20):
        await asyncio.sleep(3)
        print("Action!")

async def background_task_creator(message: types.Message) -> None:
    """Creates background tasks"""
    asyncio.create_task(background_on_action())
    await message.reply("Another one background task create")

async def on_bot_start_up(dispatcher: Dispatcher) -> None:
    """List of actions which should be done before bot start"""
    asyncio.create_task(check_notifications())  # Creates background task

def create_bot_factory() -> None:
    """Creates and starts the bot"""
    # Create a Redis client
    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Create an instance of the bot and the dispatcher

    # Bot endpoints block:
    dp.register_message_handler(background_task_creator)

    # Start the bot
    executor.start_polling(dp, skip_updates=True, on_startup=on_bot_start_up)

# Start the bot
if __name__ == '__main__':
    create_bot_factory()