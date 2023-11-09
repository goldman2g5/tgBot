import asyncio
import time

import aiohttp
import requests
from aiogram import Dispatcher, types
from aiogram.utils.callback_data import CallbackData
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bot import bot, dp
from api import API_URL

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
    print(channel_telegram_id)
    print(channel_name)
    await bot.send_message(channel_name, "It's time for a promotional post!", reply_markup=markup)


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
        response = requests.get(f'{API_URL}/Notification', verify=False)
        response.raise_for_status()
        bump_notifications = response.json()
        for notification in bump_notifications:
            await send_bump_notification(notification)

        # Fetch subscription notifications from the API
        response = requests.get(f'{API_URL}/Subscription/CheckExpiredSubscriptions', verify=False)
        response.raise_for_status()
        sub_notifications = response.json()
        for notification in sub_notifications:
            await send_sub_notification(notification)

        # Fetch promo posts from the API
        response = requests.get(f'{API_URL}/Notification/GetPromoPosts', verify=False)  # Replace with your endpoint
        response.raise_for_status()
        promo_notifications = response.json()
        print(promo_notifications)
        for notification in promo_notifications:
            await send_promo_post_notification(notification)

            # Fetch report notifications from the API
        response = requests.get(f'{API_URL}/Notification/GetReportNotifications', verify=False)
        response.raise_for_status()
        report_notifications = response.json()
        for notification in report_notifications:
            await send_report_notification(notification)


    except requests.RequestException as e:
        # Log the error
        print(f"Error fetching notifications: {str(e)}")


view_report_cb = CallbackData('report', 'action', 'id')


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('viewreport_'))
async def handle_view_report(callback_query: types.CallbackQuery):
    # Extract the report ID from the callback query data
    _, report_id = callback_query.data.split('_')
    report_id = int(report_id)  # Convert report_id to an integer if needed

    async with aiohttp.ClientSession() as session:
        # Assuming your API endpoint to get the report looks like this
        report_url = f'{API_URL}/Auth/Report/{report_id}'
        print(report_url)

        # Make a GET request to your API endpoint
        async with session.get(report_url, ssl=False) as response:
            if response.status == 200:

                report_data = await response.json()  # Get the report data as JSON
                # Format a message to send to the user
                report_details = (f"Channel Name: {report_data['channelName']}\n"
                                  f"Channel URL: {report_data['channelWebUrl']}\n"
                                  f"Reportee Name: {report_data['reporteeName']}\n"
                                  f"Report Time: {report_data['reportTime']}\n"
                                  f"Text: {report_data['text']}\n"
                                  f"Reason: {report_data['reason']}\n")
                # Prepare the inline keyboard markup
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("Hide", callback_data=view_report_cb.new(action="hide", id=report_id)))
                markup.add(
                    types.InlineKeyboardButton("Skip", callback_data=view_report_cb.new(action="skip", id=report_id)))
                markup.add(types.InlineKeyboardButton("Contact Owner",
                                                      callback_data=view_report_cb.new(action="contact", id=report_id)))

                # Send the report details to the user with inline buttons
                await bot.send_message(callback_query.from_user.id, report_details, reply_markup=markup)
            else:
                # Send an error message if something goes wrong
                await bot.send_message(callback_query.from_user.id, "Could not retrieve the report details.")

                # Always answer the callback query
            await callback_query.answer()

    # Always answer the callback query, even if you do not send a message to the user
    await callback_query.answer()


# Handlers for the inline button actions
@dp.callback_query_handler(view_report_cb.filter(action="hide"))
async def handle_hide(callback_query: types.CallbackQuery, callback_data: dict):
    # Implement hide logic
    await callback_query.answer("Report hidden.")


@dp.callback_query_handler(view_report_cb.filter(action="skip"))
async def handle_skip(callback_query: types.CallbackQuery, callback_data: dict):
    # Implement skip logic
    await callback_query.answer("Report skipped.")


@dp.callback_query_handler(view_report_cb.filter(action="contact"))
async def handle_contact_owner(callback_query: types.CallbackQuery, callback_data: dict):
    # Implement contact owner logic
    await callback_query.answer("Contacting owner.")


async def check_notifications():
    # Fetch notifications from the API
    await fetch_notifications()


async def start_notification_service(dispatcher: Dispatcher):
    # Start the APScheduler scheduler
    scheduler.add_job(check_notifications, IntervalTrigger(seconds=15))
    scheduler.start()
