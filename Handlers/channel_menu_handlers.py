import datetime
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import get_notification_status, toggle_notification_status, bump_channel
from bot import dp, bot
from misc import open_menu


# Handler for channel menu callbacks
@dp.callback_query_handler(
    lambda c: c.data.startswith("channel_") or c.data == "back_to_menu")
async def process_channel_menu(callback_query: types.CallbackQuery):
    if callback_query.data == "back_to_menu":
        # Open the main menu
        await open_menu(callback_query.message.chat.id)

        # # Clear all messages produced by the module
        # await clear_module_messages(callback_query.message.chat.id)

    channel_id = int(callback_query.data.split("_")[1])

    # Create inline buttons for channel menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Edit info", callback_data=f"customization_{channel_id}"),
        InlineKeyboardButton("Subscription", callback_data=f"subscription_{channel_id}"),
        InlineKeyboardButton("Notifications", callback_data=f"notifications_{channel_id}"),
        InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}"),
        InlineKeyboardButton("Customization", callback_data=f"customization_{channel_id}"),
        InlineKeyboardButton("Back to Menu", callback_data="manage_channels")
    )

    if callback_query.message.reply_markup:
        # Edit the existing message with the updated inline keyboard
        await bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer("Channel menu:", reply_markup=markup)


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


# Handler for notifications button
@dp.callback_query_handler(lambda c: c.data.startswith("notifications_"))
async def process_notifications_button(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])

    notifications_enabled = get_notification_status(channel_id)

    if notifications_enabled is None:
        await callback_query.message.answer("Channel not found.")
        return

    # Create inline buttons for notifications menu
    markup = create_notifications_menu(channel_id, notifications_enabled)

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
    markup = create_notifications_menu(channel_id, new_notifications_enabled)

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
        InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}")
    )

    with open('subscription_image.jpg', 'rb') as photo_file:
        if callback_query.message.reply_markup:
            # Edit the existing message with the updated inline keyboard
            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=markup
            )
        else:
            # Send a new message with the photo and inline keyboard
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


# Handler for bump button callback
@dp.callback_query_handler(lambda c: c.data.startswith("bump_"))
async def process_bump_button(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])

    # Call the API method to bump the channel
    response = await bump_channel(channel_id)

    if response is not None:
        if response.status_code == 204:
            await callback_query.answer("Channel bumped successfully.")
        elif response.status_code == 400:
            time_left = response.headers.get("X-TimeLeft")
            if time_left:
                time_left = int(time_left)
                duration = datetime.timedelta(seconds=time_left)
                hours = duration.seconds // 3600
                minutes = (duration.seconds // 60) % 60
                time_left_str = f"{hours} hours and {minutes} minutes"
                await callback_query.answer(f"Next bump available in {time_left_str}.")
            else:
                await callback_query.answer("Failed to bump the channel.")
        else:
            await callback_query.answer("Failed to bump the channel.")
    else:
        await callback_query.answer("An error occurred while attempting to bump the channel.")
