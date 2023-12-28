import asyncio
import time

import aiohttp
import requests
from aiogram import Dispatcher, types
from aiogram.utils.callback_data import CallbackData
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bot import bot, dp
from api import API_URL, default_headers

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

    await bot.send_message(telegram_chat_id, f"Your subscription for {channel_name} has expired!")


async def send_promo_post_notification(notification):
    channel_telegram_id = notification['channelTelegramId']
    channel_id = notification['channelId']
    channel_name = notification['channelTelegramName']

    # Send the notification to the user using the bot
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Promo", callback_data=f"promo_{channel_id}_delete"),
    )
    await bot.send_message(channel_telegram_id, "It's time for a promotional post!", reply_markup=markup)


async def send_report_notification(notification):
    reportee_name = notification['reporteeName']
    channel_name = notification['channelName']
    report_id = notification['reportId']
    print(f"{report_id} bebra")
    message = f"New report from {reportee_name} in channel {channel_name}."

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("View full info", callback_data=f"viewreport_{report_id}")
    )

    # Send the notification to each target chat ID
    for telegram_chat_id in notification['targets']:
        if telegram_chat_id:  # Checking if chat ID is not null
            await bot.send_message(telegram_chat_id, message, reply_markup=markup)
            time.sleep(1)


async def fetch_notifications():
    try:
        # Fetch bump notifications from the API
        response = requests.get(f'{API_URL}/Notification', verify=False, headers=default_headers)
        response.raise_for_status()
        bump_notifications = response.json()
        for notification in bump_notifications:
            time.sleep(1)
            await send_bump_notification(notification)

        # Fetch subscription notifications from the API
        response = requests.get(f'{API_URL}/Subscription/CheckExpiredSubscriptions', verify=False, headers=default_headers)
        response.raise_for_status()
        sub_notifications = response.json()
        for notification in sub_notifications:
            time.sleep(1)
            await send_sub_notification(notification)

        # Fetch promo posts from the API
        response = requests.get(f'{API_URL}/Notification/GetPromoPosts', verify=False, headers=default_headers)  # Replace with your endpoint
        response.raise_for_status()
        promo_notifications = response.json()
        # print(promo_notifications)
        for notification in promo_notifications:
            time.sleep(1)
            await send_promo_post_notification(notification)

        # Fetch report notifications from the API
        #response = requests.get(f'{API_URL}/Notification/GetReportNotifications', verify=False)
        #response.raise_for_status()
        #report_notifications = response.json()
        #for notification in report_notifications:
            #await send_report_notification(notification)


    except requests.RequestException as e:
        # Log the error
        print(f"Error fetching notifications: {str(e)}")


async def check_notifications():
    # Fetch notifications from the API
    await fetch_notifications()


async def start_notification_service(dispatcher: Dispatcher):
    print("Starting notification service...")
    # scheduler.add_job(check_notifications, IntervalTrigger(seconds=5))
    scheduler.start()
