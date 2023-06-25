from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot
import logging

notification_delay = 1


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
async def open_menu(chat_id: int, message_id: int):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
               InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup,
            text="Main menu"
        )
    except Exception as e:
        # Open the menu
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("Add Channel", callback_data="add_channel"),
                   InlineKeyboardButton("Manage Channels", callback_data="manage_channels"))
        await bot.send_message(chat_id, "Menu:", reply_markup=markup)
        print(e)




# Common function to create inline buttons for notifications menu
def create_notifications_menu(channel_id, notifications_enabled):
    markup = InlineKeyboardMarkup(row_width=1)
    toggle_text = "Disable" if notifications_enabled else "Enable"
    toggle_callback_data = f"toggle_notifications_{channel_id}"
    markup.add(
        InlineKeyboardButton(f"{toggle_text} Notifications", callback_data=toggle_callback_data),
        InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}")
    )
    return markup
