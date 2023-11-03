import base64
import urllib
from asyncio import exceptions
from urllib import parse
from urllib.parse import parse_qs

from aiogram import types
from aiogram.dispatcher.filters import Command, state
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import *
from bot import dp, bot
from misc import open_menu
from states import AddChannelStates
from api import API_URL


def send_message(connection_id, username, user_id):
    url = "http://46.39.232.190:8053/api/Auth"
    # url = "https://localhost:7256/api/Auth"
    payload = {
        "Username": username,
        "UserId": user_id,
        "Unique_key": ""
    }

    params = {
        "connectionId": connection_id
    }

    response = requests.post(url, json=payload, params=params, verify=False)

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message")
        print(response)

def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')

@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    username = message.from_user.username
    user_id = message.from_user.id
    args = message.get_args()

    # Downloading the user's avatar
    avatar_bytes = None  # Default to None in case no profile photo is found
    profile_photos = await bot.get_user_profile_photos(user_id, limit=1)

    if profile_photos.photos:  # Check if the user has a profile photo
        photo = profile_photos.photos[0][0]  # latest photo, smallest size
        file = await bot.get_file(photo.file_id)
        file_path = file.file_path
        url = f"https://api.telegram.org/file/bot6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4/{file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                avatar_bytes = await response.read()  # byte array of the photo

    # Save user info
    avatar_str = bytes_to_base64(avatar_bytes) if avatar_bytes else None
    # save_user_info(user_id, message.chat.id, username, avatar_str)

    if args:
        connection_id = args
        print(connection_id)
        send_message(connection_id, username, user_id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Got it", callback_data="remove_authorize_msg"))
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.send_message(message.chat.id, "You are authorized, go back to the website", reply_markup=markup)
        return

    # Write user info to the database

    # Open the menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))
    await bot.send_message(message.chat.id, "Menu:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'remove_authorize_msg')
async def remove_authorization_messages(callback_query: types.CallbackQuery):
    # Deleting the success message
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback_query: types.CallbackQuery):
    # Open the main menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))

    if callback_query.message.reply_markup:
        # Edit the existing message with the updated inline keyboard
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup,
            text=f"Main menu:",
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer(text="Main menu:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def add_channel_handler(callback_query: types.CallbackQuery):
    # Set the state
    await AddChannelStates.waiting_for_channel_name.set()
    message = await callback_query.message.answer("Please enter the channel name:",
                                                  reply_markup=InlineKeyboardMarkup(row_width=1)
                                                  .add(InlineKeyboardButton("Cancel",
                                                                            callback_data="cancel_enter_channel_name")))
    await dp.current_state().update_data(channel_name_message_id=message.message_id)


@dp.callback_query_handler(lambda c: c.data == "manage_channels")
async def manage_channels_handler(callback_query: types.CallbackQuery):
    # Get the user's ID
    user_id = callback_query.from_user.id
    print(user_id)
    # Retrieve the user's channels from the API
    channels = get_user_channels(user_id)

    if channels:
        # Create inline buttons for each channel
        markup = InlineKeyboardMarkup(row_width=1)
        for channel in channels:
            button_text = f"{channel['name']} - {channel['description']}"
            callback_data = f"channel_{channel['id']}_{channel['name']}"
            markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
        markup.add(InlineKeyboardButton("Back to Menu", callback_data="back_to_menu"))
        if callback_query.message.reply_markup:
            # Edit the existing message with the updated inline keyboard
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=markup,
                text=f"Your channels:",
            )
        else:
            # Send a new message with the inline keyboard
            await callback_query.message.answer(text="Your channels:", reply_markup=markup)
    else:
        await callback_query.message.answer("You don't have any channels.")
