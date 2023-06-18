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

# Redis connection setup
redis_host = "localhost"
redis_port = 6379
redis_queue_name = "notification_queue"
redis_conn = redis.Redis(host=redis_host, port=redis_port)


# Notification service setup
class NotificationService:
    def __init__(self):
        self.bot = None

    async def start(self, bot):
        self.bot = bot
        await self.process_notifications()

    async def process_notifications(self):
        while True:
            notification = self.get_notification()
            if notification:
                await self.send_notification(notification)
            else:
                await asyncio.sleep(1800)  # Wait for 30 minutes

    def get_notification(self):
        notification = redis_conn.blpop(redis_queue_name, timeout=0)
        if notification:
            notification = json.loads(notification[1])
        return notification

    async def send_notification(self, notification):
        print("jopa")
        # Make a request to the API to get the notification details
        response = requests.get("http://localhost:8053/Api/Notifications")
        if response.status_code == 200:
            notifications = response.json()
            for notification in notifications:
                if notification["telegramChatId"] == notification["telegramUserId"]:
                    await self.bot.send_message(
                        chat_id=notification["telegramChatId"],
                        text=f"You have a new notification in {notification['channelName']}:\n{notification['sendTime']}"
                    )
        else:
            print("Failed to retrieve notifications.")


async def background_on_start() -> None:
    """background task which is created when bot starts"""
    while True:
        await asyncio.sleep(5)
        print("Hello World!")

async def background_on_start() -> None:
    """background task which is created when bot starts"""
    while True:
        await asyncio.sleep(5)
        print("Hello World!")


async def background_on_action() -> None:
    """background task which is created when user asked"""
    for _ in range(20):
        await asyncio.sleep(3)
        print("Action!")


async def background_task_creator(message: types.Message) -> None:
    """Creates background tasks"""
    asyncio.create_task(background_on_action())
    await message.reply("Another one background task create")


async def on_bot_start_up(dispatcher: Dispatcher) -> None:
    """List of actions which should be done before bot start"""
    notification_service = NotificationService()
    notification_service.bot = bot
    # asyncio.create_task(notification_service.process_notifications())
    asyncio.create_task(background_on_start())  # creates background task


def create_bot_factory() -> None:
    """Creates and starts the bot"""
    # bot endpoints block:
    dp.register_message_handler(
        background_task_creator,
    )
    # start bot
    executor.start_polling(dp, skip_updates=True, on_startup=on_bot_start_up)




# Start the bot
if __name__ == '__main__':
    from aiogram import executor

    create_bot_factory()
