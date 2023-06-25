from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import *
from bot import dp
from misc import open_menu
from states import AddChannelStates


# Handler for the /start command
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    # Write user info to the database
    save_user_info(message.from_user.id, message.chat.id)

    # Open the menu
    await open_menu(message.chat.id)


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
                callback_data = f"channel_{channel['id']}_{channel['name']}"
                markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))
            await callback_query.message.answer("Your channels:", reply_markup=markup)
        else:
            await callback_query.message.answer("You don't have any channels.")
