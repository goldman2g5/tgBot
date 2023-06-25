from aiogram import types
from aiogram.dispatcher.filters import Command, state
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import *
from bot import dp, bot
from misc import open_menu
from states import AddChannelStates


# Handler for the /start command
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    # Write user info to the database
    save_user_info(message.from_user.id, message.chat.id)

    # Open the menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))
    await bot.send_message(message.chat.id, "Menu:", reply_markup=markup)


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
    message = await callback_query.message.answer("Please enter the channel name:")
    print(message.message_id)

    await dp.current_state().update_data(channel_name_message_id=message.message_id)


@dp.callback_query_handler(lambda c: c.data == "manage_channels")
async def manage_channels_handler(callback_query: types.CallbackQuery):
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
