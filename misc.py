from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot
import logging


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