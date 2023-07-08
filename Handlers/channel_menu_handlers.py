import asyncio
import datetime
import json

import aiohttp
import requests
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from api import get_notification_status, toggle_notification_status, bump_channel, get_tags, save_tags, \
    get_channel_tags, get_subscriptions_from_api, subscribe_channel
from bot import dp, bot
from misc import open_menu, create_notifications_menu


@dp.callback_query_handler(lambda c: c.data.startswith("channel_"))
async def channel_menu_handler(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    # Create inline buttons for channel menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Subscription", callback_data=f"subscription_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Notifications", callback_data=f"notifications_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}"),
        InlineKeyboardButton("Customization", callback_data=f"customization_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Back to Menu", callback_data="manage_channels")
    )

    if callback_query.message.reply_markup:
        # Edit the existing message with the updated inline keyboard
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup,
            text=f"{channel_name} Channel menu:",
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer(reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith("customization_"))
async def customization_handler(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    # Create inline buttons for customization options
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Tags", callback_data=f"tags_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Description", callback_data=f"description_{channel_id}"),
        InlineKeyboardButton("Update Data", callback_data=f"update_data_{channel_id}"),
        InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}_{channel_name}")
    )

    # Edit a message with the customization options
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"customization options: {channel_name}",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("tags_"))
async def tags_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    # Вот эту функцию поменять местами
    # Retrieve the current tags dictionary from the state, or initialize it if it doesn't exist
    async with state.proxy() as data:
        tags = await get_channel_tags(channel_id)  # Use get_channel_tags instead of get_tags
        data["tags"] = tags

    # С вот этой
    # Либо вообще хендлер отдельный вьебать
    # Extract the tag and action from the callback data
    callback_arguments = callback_query.data.split("_")
    if len(callback_arguments) > 3:
        action = callback_query.data.split("_")[3]
        tag = callback_query.data.split("_")[4]
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
        callback_data = f"tags_{channel_id}_{channel_name}_toggle_{tag}"
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))

    markup.add(InlineKeyboardButton("Save", callback_data=f"save_tags_{channel_id}"))
    markup.add(InlineKeyboardButton("Back", callback_data=f"customization_{channel_id}_{channel_name}"))

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
    channel_name = callback_query.data.split("_")[2]

    notifications_enabled = get_notification_status(channel_id)

    if notifications_enabled is None:
        await callback_query.message.answer("Channel not found.")
        return

    # Create inline buttons for notifications menu
    markup = create_notifications_menu(channel_id, channel_name, notifications_enabled)

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
    channel_name = callback_query.data.split("_")[3]

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
    markup = create_notifications_menu(channel_id, channel_name, new_notifications_enabled)

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
    channel_name = callback_query.data.split("_")[2]

    # Retrieve subscription data from the API
    subscriptions = get_subscriptions_from_api()
    if subscriptions is not None:
        # Create inline buttons for subscription options using the retrieved data
        markup = InlineKeyboardMarkup(row_width=1)
        for subscription in subscriptions:
            markup.add(
                InlineKeyboardButton(subscription['name'],
                                     callback_data=f"subscriptionchoice_{channel_id}_{channel_name}_{subscription['id']}"),
            )
        markup.add(
            InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}_{channel_name}")
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
    else:
        # Handle error if API request fails
        await callback_query.answer("Failed to retrieve subscription data from the API.")


YCASSATOKEN = "381764678:TEST:59527"


# Handler for subscription choice buttons
@dp.callback_query_handler(lambda c: c.data.startswith("subscriptionchoice_"))
async def process_subscription_choice(callback_query: types.CallbackQuery):
    choice_data = callback_query.data.split("_")
    channel_id = int(choice_data[1])
    channel_name = choice_data[2]
    subscription_type = choice_data[3]

    # Retrieve subscription data from the API
    subscriptions = get_subscriptions_from_api()
    if subscriptions is not None:
        # Find the selected subscription by its ID
        selected_subscription = next((sub for sub in subscriptions if str(sub['id']) == subscription_type), None)
        if selected_subscription:
            # Prepare the invoice details
            invoice_title = f"Оформление подписки на {channel_name}"
            invoice_description = "Тестовое описание товара"
            invoice_payload = f"{channel_id}_{channel_name}_{selected_subscription['id']}_{selected_subscription['name']}"
            invoice_currency = "RUB"
            invoice_prices = [{"label": "Руб", "amount": selected_subscription['price'] * 100}]

            # Send the invoice
            await bot.send_invoice(
                chat_id=callback_query.from_user.id,
                title=invoice_title,
                description=invoice_description,
                payload=invoice_payload,
                provider_token=YCASSATOKEN,
                currency=invoice_currency,
                start_parameter="test_bot",
                prices=invoice_prices
            )
        else:
            await callback_query.answer("Invalid subscription choice.")
    else:
        await callback_query.answer("Failed to retrieve subscription data from the API.")


@dp.pre_checkout_query_handler()
async def proccess_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_pay(message: types.Message):
    choice_data = message.successful_payment.invoice_payload.split("_")
    channel_id = int(choice_data[0])
    channel_name = choice_data[1]
    subscription_id = choice_data[2]
    subscription_type = choice_data[3]

    if message.successful_payment.invoice_payload.startswith(f"{channel_id}"):
        await bot.send_message(
            message.from_user.id,
            f"You have bought a {subscription_type} subscription for the channel {channel_name}"
        )

        # Subscribe channel
        success, response_message = subscribe_channel(channel_id, subscription_id)

        if success:
            await bot.send_message(
                message.from_user.id,
                response_message
            )
        else:
            await bot.send_message(
                message.from_user.id,
                response_message
            )


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

    # Check if the callback data contains "delete" keyword
    if "delete" in callback_query.data:
        # Wait for 30 seconds before deleting the message
        await asyncio.sleep(10)
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
