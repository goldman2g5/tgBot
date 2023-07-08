import requests
from aiogram import Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from Handlers.add_channel_handlers import *

# Initialize APScheduler scheduler
scheduler = AsyncIOScheduler()


async def send_bump_notification(notification):
    channel_name = notification['channelName']
    telegram_chat_id = notification['telegramChatId']
    channel_id = notification['channelId']

    # Send the notification to the user using the bot
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}_delete"),
    )
    await bot.send_message(telegram_chat_id, f"It's time to bump {channel_name}!", reply_markup=markup)


async def send_sub_notification(notification):
    channel_name = notification['channelName']
    telegram_chat_id = notification['telegramChatId']
    channel_id = notification['channelId']

    await bot.send_message(telegram_chat_id, f"Your subsciption for {channel_name} has expired!")


async def fetch_notifications():
    try:
        # Fetch notifications from the API
        response = requests.get('http://localhost:8053/api/Notification')
        response.raise_for_status()  # Raise an exception for non-2xx responses

        bump_notifications = response.json()

        # Process each notification
        for notification in bump_notifications:
            await send_bump_notification(notification)

        response = requests.get('http://localhost:8053/api/Subscription/CheckExpiredSubscriptions')
        response.raise_for_status()  # Raise an exception for non-2xx responses

        sub_notifications = response.json()

        # Process each notification
        for notification in sub_notifications:
            await send_sub_notification(notification)



    except requests.RequestException as e:
        # Log the error
        print(f"Error fetching notifications: {str(e)}")


async def check_notifications():
    # Fetch notifications from the API
    await fetch_notifications()


async def start_notification_service(dispatcher: Dispatcher):
    # Start the APScheduler scheduler
    scheduler.add_job(check_notifications, IntervalTrigger(minutes=1))
    scheduler.start()
