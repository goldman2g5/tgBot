import base64
import logging
from typing import List

import requests
import io
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from aiogram.utils import exceptions

# Set the log level for debugging
logging.basicConfig(level=logging.INFO)

# Initialize the bot and dispatcher
bot = Bot(token="6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Class describing the states for adding a channel
class AddChannelStates(StatesGroup):
    waiting_for_channel_name = State()
    waiting_for_check = State()
    waiting_for_channel_description = State()
    waiting_for_user_id = State()  # New state for user ID


# Function to check if the bot is added to the channel
async def check_bot_in_channel(channel_name: str) -> bool:
    try:
        chat = await bot.get_chat(channel_name)
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status == "administrator":
            return True
    except Exception as e:
        logging.error(f"Error checking bot membership: {e}")
    return False


# Function to open the menu
async def open_menu(chat_id: int):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))
    await bot.send_message(chat_id, "Menu:", reply_markup=markup)


# Handler for the /start command
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    # Open the menu
    await open_menu(message.chat.id)


# Function to retrieve user's channels from the API
def get_user_channels(user_id: int) -> List[dict]:
    api_url = f"http://localhost:8053/api/Channel/ByUser/{user_id}"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        return []


# Handler for menu button callbacks
@dp.callback_query_handler(lambda c: c.data in ["add_channel", "manage_channels"])
async def process_menu_callbacks(callback_query: types.CallbackQuery):
    if callback_query.data == "add_channel":
        await AddChannelStates.waiting_for_channel_name.set()
        await callback_query.message.answer("Please enter the channel name:")
    elif callback_query.data == "manage_channels":
        # Get the user's ID
        user_id = callback_query.from_user.id

        # Retrieve the user's channels from the API
        channels = get_user_channels(user_id)

        if channels:
            # Create inline buttons for each channel
            markup = InlineKeyboardMarkup(row_width=1)
            for channel in channels:
                button_text = f"{channel['name']} - {channel['description']}"
                callback_data = f"channel_{channel['id']}"
                markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
            await callback_query.message.answer("Your channels:", reply_markup=markup)
        else:
            await callback_query.message.answer("You don't have any channels.")


# Handler for channel menu callbacks
@dp.callback_query_handler(lambda c: c.data.startswith("channel_") or c.data == "back_to_menu")
async def process_channel_menu(callback_query: types.CallbackQuery):
    if callback_query.data == "back_to_menu":
        # Open the main menu
        await open_menu(callback_query.message.chat.id)
        return

    channel_id = int(callback_query.data.split("_")[1])

    # Create inline buttons for channel menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Subscription", callback_data=f"subscription_{channel_id}"),
        InlineKeyboardButton("Notifications", callback_data=f"notifications_{channel_id}"),
        InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}"),
        InlineKeyboardButton("Customization", callback_data=f"customization_{channel_id}"),
        InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    )

    await callback_query.message.answer("Channel menu:", reply_markup=markup)


# Handler for entering the channel name
@dp.message_handler(state=AddChannelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    channel_name = "@" + message.text

    # Save the channel name in the context
    await state.update_data(channel_name=channel_name)

    # Create the "Add Bot" button and send the message
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Check", callback_data="add_bot"))
    await message.answer("To add a channel for monitoring, "
                         "you need to add the bot to the channel.", reply_markup=markup)

    await AddChannelStates.waiting_for_check.set()


# Handler for the "Add Bot" button
@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="add_bot")
async def process_add_bot(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_name = data.get("channel_name")

    user = callback_query.from_user

    # Check if the bot is added to the channel
    if await check_bot_in_channel(channel_name):
        # Check if the user is an administrator of the channel
        try:
            chat = await bot.get_chat(channel_name)
            member = await bot.get_chat_member(chat.id, user.id)
            if member.status in ("administrator", "creator"):
                # Store channel_name and user_id in the state
                await state.update_data(channel_name=channel_name, user_id=user.id)
                await callback_query.message.answer("Success! Bot added to the channel.")
                await callback_query.message.answer("Please enter the channel description:")
                await AddChannelStates.waiting_for_channel_description.set()
                return
            else:
                message = "Error: You are not an administrator of the specified channel."
        except Exception as e:
            message = f"Error occurred during verification: {e}"
    else:
        message = "Error: Bot was not added to the channel."

    await callback_query.message.answer(message)


# Handler for entering the channel description
@dp.message_handler(state=AddChannelStates.waiting_for_channel_description)
async def process_channel_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    user_id = data.get("user_id")  # Retrieve the user's ID from the state

    if channel_name is None:
        # Handle the case when channel_name is not available in the state
        await message.answer("Error: Failed to get channel information.")
        await state.finish()
        return

    channel_description = message.text

    # Save channel information to the database
    if await save_channel_information(channel_name, channel_description, user_id):  # Pass user_id to the function
        await message.answer("Channel information saved successfully.")
    else:
        await message.answer("Failed to save channel information.")

    await open_menu(message.chat.id)

    await state.finish()


# Function to save channel information to the database
async def save_channel_information(channel_name: str, channel_description: str, user_id: int) -> bool:
    # Retrieve the member count
    chat = await bot.get_chat(channel_name)
    members_count = await bot.get_chat_members_count(chat.id)

    # Get the channel avatar
    avatar_bytes = None
    if chat.photo:
        avatar = chat.photo
        avatar_file = io.BytesIO()
        await avatar.download_small(destination=avatar_file)
        avatar_bytes = avatar_file.getvalue()

    # Convert avatar bytes to base64 string
    avatar_base64 = base64.b64encode(avatar_bytes).decode() if avatar_bytes else None

    # Write channel information to the database using the API
    api_url = "http://localhost:8053/api/Channel"
    print(user_id)

    data = {
        "id": 0,
        "name": channel_name,
        "description": channel_description,
        "members": members_count,
        "avatar": avatar_base64,
        "user": user_id  # Add the user ID to the data payload
    }

    response = requests.post(api_url, json=data)
    print(response.text)
    if response.status_code == 201:
        return True
    else:
        return False


if __name__ == "__main__":
    # Start the bot
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
