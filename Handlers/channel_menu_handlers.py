import datetime
import json

import requests
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import get_notification_status, toggle_notification_status, bump_channel, get_tags, save_tags
from bot import dp, bot
from misc import open_menu, create_notifications_menu


@dp.callback_query_handler(lambda c: c.data.startswith("channel_"))
async def channel_menu_handler(callback_query: types.CallbackQuery):
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
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup,
            text=f"Channel menu:",
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer(reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith("customization_"))
async def customization_handler(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])

    # Create inline buttons for customization options
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Tags", callback_data=f"tags_{channel_id}"),
        InlineKeyboardButton("Description", callback_data=f"description_{channel_id}"),
        InlineKeyboardButton("Update Data", callback_data=f"update_data_{channel_id}"),
        InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}")
    )

    # Edit a message with the customization options
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"ИМЯ КАНАЛА СЮДА ВСТАВЬ ДОЛБАЕБ КАК НИЬБУДЬ СУКА customization options:",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("tags_"))
async def tags_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])

    # Retrieve the current tags dictionary from the state, or initialize it if it doesn't exist
    async with state.proxy() as data:
        tags = data.get("tags")
        if tags is None:
            tags = await get_tags()
            data["tags"] = tags

    # Extract the tag and action from the callback data
    callback_arguments = callback_query.data.split("_")
    channel_id = callback_query.data.split("_")[1]
    if len(callback_arguments) > 2:
        action = callback_query.data.split("_")[2]
        tag = callback_query.data.split("_")[3]
        # Update the status of the clicked tag
        if action == "toggle":
            tags[tag] = not tags[tag]

    # Update the state with the modified tags dictionary
    async with state.proxy() as data:
        data["tags"] = tags

    # Create inline buttons for tags
    markup = InlineKeyboardMarkup(row_width=1)
    for tag, selected in tags.items():
        button_text = f"{tag} ✅" if selected else f"{tag} ❌"
        callback_data = f"tags_{channel_id}_toggle_{tag}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))

    markup.add(InlineKeyboardButton("Save", callback_data=f"save_tags_{channel_id}"))
    markup.add(InlineKeyboardButton("Back", callback_data=f"customization_{channel_id}"))

    # Send a message with available tags
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Available tags:",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("save_tags_"))
async def save_tags_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[2])

    async with state.proxy() as data:
        tags = data.get("tags")
        if tags is None:
            tags = await get_tags()
            data["tags"] = tags

    # Retrieve the current tags dictionary from the state
    async with state.proxy() as data:
        tags = data.get("tags", {})

    # Send the tags to the API
    save_tags(channel_id, tags)

    # Extract the selected tags as a comma-separated string
    selected_tags = [tag for tag, selected in tags.items() if selected]
    tags_string = ", ".join(selected_tags)

    # Send a message indicating that the customization is saved
    await callback_query.answer(f"Customization saved with tags: {tags_string}")


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
