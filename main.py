import base64
import io
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Handlers.menu_handlers import open_menu
from api import *
from bot import bot, dp
from states import AddChannelStates


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
        InlineKeyboardButton("Edit info", callback_data=f"customization_{channel_id}"),
        InlineKeyboardButton("Subscription", callback_data=f"subscription_{channel_id}"),
        InlineKeyboardButton("Notifications", callback_data=f"notifications_{channel_id}"),
        InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}"),
        InlineKeyboardButton("Customization", callback_data=f"customization_{channel_id}"),
        InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    )

    await callback_query.message.answer("Channel menu:", reply_markup=markup)


# Handler for notifications button
@dp.callback_query_handler(lambda c: c.data.startswith("notifications_"))
async def process_notifications_button(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])

    notifications_enabled = get_notification_status(channel_id)

    if notifications_enabled is None:
        await callback_query.message.answer("Channel not found.")
        return

    # Create inline buttons for notifications menu
    markup = InlineKeyboardMarkup(row_width=1)
    toggle_text = "Disable" if notifications_enabled else "Enable"
    toggle_callback_data = f"toggle_notifications_{channel_id}"
    markup.add(
        InlineKeyboardButton(f"{toggle_text} Notifications", callback_data=toggle_callback_data),
        InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    )

    # Edit the existing message with the updated notification status and toggle button
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Notifications is {'on' if notifications_enabled else 'off'}",
        reply_markup=markup
    )


# Handler for toggle/disable button
@dp.callback_query_handler(lambda c: c.data.startswith("toggle_notifications_"))
async def process_toggle_notifications_button(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[2])

    notifications_enabled = get_notification_status(channel_id)

    if notifications_enabled is None:
        await callback_query.message.answer("Channel not found.")
        return

    # Toggle the notification status
    new_notifications_enabled = not notifications_enabled

    # Update the notification status in the API
    success = toggle_notification_status(channel_id, new_notifications_enabled)

    if not success:
        await callback_query.message.answer("Failed to toggle notifications.")
        return

    # Create inline buttons for notifications menu
    markup = InlineKeyboardMarkup(row_width=1)
    toggle_text = "Disable" if new_notifications_enabled else "Enable"
    toggle_callback_data = f"toggle_notifications_{channel_id}"
    markup.add(
        InlineKeyboardButton(f"{toggle_text} Notifications", callback_data=toggle_callback_data),
        InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    )

    # Edit the existing message with the updated notification status and toggle button
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Notifications is {'on' if new_notifications_enabled else 'off'}",
        reply_markup=markup
    )


# Handler for subscription button
@dp.callback_query_handler(lambda c: c.data.startswith("subscription_"))
async def process_subscription_button(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])

    # Create inline buttons for subscription options
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Lite", callback_data=f"subscription_choice_{channel_id}_lite"),
        InlineKeyboardButton("Pro", callback_data=f"subscription_choice_{channel_id}_pro"),
        InlineKeyboardButton("Premium", callback_data=f"subscription_choice_{channel_id}_premium"),
        InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    )

    with open('subscription_image.jpg', 'rb') as photo_file:
        await callback_query.message.reply_photo(photo_file, reply_markup=markup)


# Handler for subscription choice buttons
@dp.callback_query_handler(lambda c: c.data.startswith("subscription_choice_"))
async def process_subscription_choice(callback_query: types.CallbackQuery):
    choice_data = callback_query.data.split("_")
    channel_id = int(choice_data[2])
    subscription_type = choice_data[3]

    # Process the subscription choice
    # ...

    # Send a message indicating the chosen subscription
    await callback_query.message.answer(f"You have chosen {subscription_type} subscription for channel {channel_id}.")


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

    # Save channel information to the database
    if await save_channel_information(channel_name, channel_description, members_count, avatar_base64,
                                      user_id):  # Pass members_count and avatar_base64 to the function
        await message.answer("Channel information saved successfully.")
    else:
        await message.answer("Failed to save channel information.")

    await open_menu(message.chat.id)

    await state.finish()


if __name__ == "__main__":
    # Start the bot
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
