import base64
import logging
import requests
import io
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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


# Handler for menu button callbacks
@dp.callback_query_handler(lambda c: c.data in ["add_channel", "manage_channels"])
async def process_menu_callbacks(callback_query: types.CallbackQuery):
    if callback_query.data == "add_channel":
        await AddChannelStates.waiting_for_channel_name.set()
        await callback_query.message.answer("Please enter the channel name:")
    elif callback_query.data == "manage_channels":
        await callback_query.message.answer("Channel management functionality is under development.")


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
                # Store channel_name in the state to access it in the next handler
                await state.update_data(channel_name=channel_name)
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

    if channel_name is None:
        # Handle the case when channel_name is not available in the state
        await message.answer("Error: Failed to get channel information.")
        await state.finish()
        return

    channel_description = message.text

    # Save channel information to the database
    if await save_channel_information(channel_name, channel_description):
        await message.answer("Channel information saved successfully.")
    else:
        await message.answer("Failed to save channel information.")

    await open_menu(message.chat.id)

    await state.finish()


# Function to save channel information to the database
async def save_channel_information(channel_name: str, channel_description: str) -> bool:
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

    data = {
        "id": 0,
        "name": channel_name,
        "description": channel_description,
        "members": members_count,
        "avatar": avatar_base64
    }

    json_data = json.dumps(data)  # Serialize the data to JSON
    print(json_data)

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
