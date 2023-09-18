import asyncio
import datetime
import json
import logging

import aiogram.types
import aiohttp
import requests
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from api import get_notification_status, toggle_notification_status, bump_channel, get_tags, save_tags, \
    get_channel_tags, get_subscriptions_from_api, subscribe_channel, get_promo_post_status, toggle_promo_post_status, \
    update_channel_language, update_channel_flag
from bot import dp, bot, client
from misc import open_menu, create_notifications_menu
from datetime import datetime, timedelta
from aiogram.dispatcher.filters.state import StatesGroup, State





def remove_negative_100(n: int) -> int:
    s = str(n)
    prefix = "-100"
    if s.startswith(prefix):
        return int(s[len(prefix):])
    return n

async def get_chat_statistics(chat_id):
    await client.stop()

    await client.start()

    me = await client.api.get_me()
    logging.info(f"Successfully logged in as {me.json()}")

    chat_id = remove_negative_100(chat_id)

    supergroup = await client.get_supergroup(supergroup_id=chat_id, force_update=True)
    print(supergroup.id)

    stats_url = await client.api.get_supergroup_full_info(supergroup_id=supergroup.id)

    print(stats_url)

    await client.stop()



    # stats = await client.api.get_chat(chat_id)

    # logging.info(f"Statistics URL: {stats_url}")

    # If you want to actually get the statistics content, you can make an HTTP request to the stats_url


@dp.callback_query_handler(lambda c: c.data.startswith("channel_"))
async def channel_menu_handler(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    chat = await bot.get_chat("@anima_shiza_autora")

    chatid = chat.id

    print(chat.id)

    await get_chat_statistics(chatid)

    # Create inline buttons for channel menu
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Subscription", callback_data=f"subscription_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Notifications", callback_data=f"notifications_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Bump", callback_data=f"bump_{channel_id}"),
        InlineKeyboardButton("Options", callback_data=f"customization_{channel_id}_{channel_name}"),
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


class DescriptionState(StatesGroup):
    waiting_for_description = State()


@dp.callback_query_handler(
    lambda c: c.data.startswith("customization_") and not c.data.startswith("customization_description"))
async def customization_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    await state.finish()

    # Create inline buttons for customization options
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Tags", callback_data=f"tags_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Additional Promotion", callback_data=f"promotion_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Description", callback_data=f"customization_description_{channel_id}"),
        InlineKeyboardButton("Language Settings", callback_data=f"lang_settings_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Back to Menu", callback_data=f"channel_{channel_id}_{channel_name}")
    )

    # Edit a message with the customization options
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Customization options: {channel_name}",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("customization_description"))
async def description_handler(callback_query: types.CallbackQuery, state: FSMContext):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Cancel", callback_data="cancel_description"))

    sent_message = await bot.send_message(callback_query.message.chat.id,
                                          "Please enter the new description for the channel:", reply_markup=markup)

    # Store the bot's message ID and the callback query's message ID in the state
    await state.set_data({
        'messages_to_delete': [sent_message.message_id]
    })

    await DescriptionState.waiting_for_description.set()


@dp.message_handler(state=DescriptionState.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    # Retrieve the message IDs from the state
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])

    # Add the user's message ID to the list
    messages_to_delete.append(message.message_id)

    # Delete all the messages
    for msg_id in messages_to_delete:
        await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)

    await state.finish()


@dp.callback_query_handler(lambda c: c.data == "cancel_description", state=DescriptionState.waiting_for_description)
async def cancel_description(callback_query: types.CallbackQuery, state: FSMContext):
    # Retrieve the message IDs from the state
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])

    for msg_id in messages_to_delete:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=msg_id)
    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith("lang_settings_"))
async def language_settings_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[2])
    channel_name = callback_query.data.split("_")[3]

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Edit Language", callback_data=f"edit_language_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Edit Flags", callback_data=f"edit_flags_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Back to Options", callback_data=f"customization_{channel_id}_{channel_name}")
    )

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Language settings for: {channel_name}",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("edit_language_"))
async def edit_language_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[2])
    channel_name = callback_query.data.split("_")[3]

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("RU", callback_data=f"language_ru_{channel_id}_{channel_name}"),
        InlineKeyboardButton("EU", callback_data=f"language_en_{channel_id}_{channel_name}"),
        InlineKeyboardButton("UA", callback_data=f"language_uk_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Back", callback_data=f"lang_settings_{channel_id}_{channel_name}")
    )

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Language settings for: {channel_name}",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("edit_flags_"))
async def edit_flags_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[2])
    channel_name = callback_query.data.split("_")[3]

    # Create inline buttons for flags options
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🇷🇺 Russia", callback_data=f"flagchoice_ru_{channel_id}_{channel_name}"),
        InlineKeyboardButton("🇬🇧 UK", callback_data=f"flagchoice_en_{channel_id}_{channel_name}"),
        InlineKeyboardButton("🇺🇦 Ukraine", callback_data=f"flagchoice_uk_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Back", callback_data=f"lang_settings_{channel_id}_{channel_name}")
    )

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Choose a flag for the channel: {channel_name}",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data.startswith("flagchoice_"))
async def flag_choice_handler(callback_query: types.CallbackQuery, state: FSMContext):
    _, flag_iso_code, channel_id, channel_name = callback_query.data.split("_")

    flag_names = {
        "ru": "ru",
        "en": "us",
        "uk": "ua"
    }

    selected_flag_name = flag_names.get(flag_iso_code, "Unknown")

    # Update flag in the backend
    update_channel_flag(channel_id, selected_flag_name)

    await bot.answer_callback_query(callback_query.id, text=f"Flag for {channel_name} updated to {selected_flag_name}")


@dp.callback_query_handler(lambda c: c.data.startswith("language_"))
async def language_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    chosen_language = callback_query.data.split("_")[1]
    channel_id = int(callback_query.data.split("_")[2])
    channel_name = callback_query.data.split("_")[3]

    # Update the channel's language in the backend
    update_channel_language(channel_id, chosen_language)

    await bot.answer_callback_query(callback_query.id, text=f"Language for {channel_name} updated to {chosen_language}")


@dp.callback_query_handler(lambda c: c.data.startswith("promotion_"))
async def promotion_submenu_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    promo_post_status = get_promo_post_status(channel_id)

    async with state.proxy() as data:
        data['promo_post_status'] = promo_post_status

    promotion_submenu_markup = await create_promo_post_menu(channel_id, channel_name, state)

    # Edit a message with the promotion submenu options
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"PromoPost is {'on' if promo_post_status else 'off'}:",
        reply_markup=promotion_submenu_markup
    )


# Handler for the "Enable/Disable Promo Post" button
@dp.callback_query_handler(lambda c: c.data.startswith("togglepromopost_"))
async def process_toggle_promo_post_button(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]

    promo_post_enabled = get_promo_post_status(channel_id)

    if promo_post_enabled is None:
        await callback_query.message.answer("Channel not found.")
        return

    # Toggle the promo post status
    new_promo_post_enabled = not promo_post_enabled

    # Update the promo post status in the API
    success = toggle_promo_post_status(channel_id, new_promo_post_enabled)

    async with state.proxy() as data:
        data['promo_post_status'] = new_promo_post_enabled

    if not success:
        await callback_query.message.answer("Failed to toggle promo post.")
        return

    # Create inline buttons for promo post menu
    markup = await create_promo_post_menu(channel_id, channel_name, state)

    # Edit the existing message with the updated promo post status and toggle button
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"PromoPost is {'on' if new_promo_post_enabled else 'off'}",
        reply_markup=markup
    )


def getChannelById(channel_id):
    try:
        response = requests.get(f"http://localhost:8053/api/Channel/{channel_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


async def create_promo_post_menu(channel_id, channel_name, state: FSMContext):
    async with state.proxy() as data:
        promo_post_enabled = data['promo_post_status']

    async with state.proxy() as data:
        if 'promo_post_time' not in data:
            channel_data = getChannelById(channel_id)
            data['promo_post_time'] = channel_data.get('promoPostTime') or '10:00:00'

        if 'promo_post_interval' not in data:
            channel_data = channel_data if 'channel_data' in locals() else getChannelById(channel_id)
            data['promo_post_interval'] = channel_data.get('promoPostInterval') or 7

        current_time = data['promo_post_time']
        current_interval = data['promo_post_interval']

    markup = InlineKeyboardMarkup(row_width=1)
    toggle_text = "Disable" if promo_post_enabled else "Enable"
    toggle_callback_data = f"togglepromopost_{channel_id}_{channel_name}"

    save_changes_data = f"savechanges_{channel_id}_{channel_name}"

    markup.add(InlineKeyboardButton(f"{toggle_text} Promo Post", callback_data=toggle_callback_data))
    markup.row(
        InlineKeyboardButton("-", callback_data=f"decreasetime_{channel_id}_{channel_name}_{current_time}"),
        InlineKeyboardButton(f"{current_time}", callback_data="noop"),
        InlineKeyboardButton("+", callback_data=f"increasetime_{channel_id}_{channel_name}_{current_time}")
    )

    markup.row(
        InlineKeyboardButton("-", callback_data=f"decreaseinterval_{channel_id}_{channel_name}_{current_interval}"),
        InlineKeyboardButton(f"{current_interval} days", callback_data="noop"),
        InlineKeyboardButton("+", callback_data=f"increaseinterval_{channel_id}_{channel_name}_{current_interval}")
    )

    markup.add(
        InlineKeyboardButton("Back", callback_data=f"customization_{channel_id}_{channel_name}"),
        InlineKeyboardButton("Save", callback_data=save_changes_data)
    )
    return markup


@dp.callback_query_handler(lambda c: c.data.startswith('decreasetime_'))
async def handle_decrease_time(callback_query: types.CallbackQuery, state: FSMContext):
    _, channel_id, channel_name, current_time = callback_query.data.split('_')
    async with state.proxy() as data:
        time_obj = datetime.strptime(current_time, '%H:%M:%S').time()
        new_time_obj = (datetime.combine(datetime.today(), time_obj) - timedelta(minutes=30)).time()
        data['promo_post_time'] = new_time_obj.strftime('%H:%M:%S')

    new_menu = await create_promo_post_menu(channel_id, channel_name, state)
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        reply_markup=new_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('increasetime_'))
async def handle_increase_time(callback_query: types.CallbackQuery, state: FSMContext):
    _, channel_id, channel_name, current_time = callback_query.data.split('_')
    async with state.proxy() as data:
        time_obj = datetime.strptime(current_time, '%H:%M:%S').time()
        new_time_obj = (datetime.combine(datetime.today(), time_obj) + timedelta(minutes=30)).time()
        data['promo_post_time'] = new_time_obj.strftime('%H:%M:%S')

    new_menu = await create_promo_post_menu(channel_id, channel_name, state)
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        reply_markup=new_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('decreaseinterval_'))
async def handle_decrease_interval(callback_query: types.CallbackQuery, state: FSMContext):
    _, channel_id, channel_name, current_interval = callback_query.data.split('_')
    async with state.proxy() as data:
        new_interval = max(1, int(current_interval) - 1)
        data['promo_post_interval'] = new_interval

    new_menu = await create_promo_post_menu(channel_id, channel_name, state)
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        reply_markup=new_menu)


@dp.callback_query_handler(lambda c: c.data.startswith('increaseinterval_'))
async def handle_increase_interval(callback_query: types.CallbackQuery, state: FSMContext):
    _, channel_id, channel_name, current_interval = callback_query.data.split('_')
    async with state.proxy() as data:
        new_interval = int(current_interval) + 1
        data['promo_post_interval'] = new_interval

    new_menu = await create_promo_post_menu(channel_id, channel_name, state)
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        reply_markup=new_menu)


def updateChannelDetails(channel_id, promo_post_time, promo_post_interval):
    try:
        payload = {
            'PromoPostTime': promo_post_time,
            'PromoPostInterval': promo_post_interval
        }

        response = requests.put(
            f"http://localhost:8053/api/Channel/UpdatePromoPostDetails/{channel_id}",
            json=payload
        )

        response.raise_for_status()
        print(response.status_code)
        print(response)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.RequestException:
        return False


@dp.callback_query_handler(lambda c: c.data.startswith('savechanges_'))
async def handle_save_changes(callback_query: types.CallbackQuery, state: FSMContext):
    _, channel_id, channel_name = callback_query.data.split('_')
    async with state.proxy() as data:
        promo_post_time = data.get('promo_post_time', '10:00:00')
        promo_post_interval = data.get('promo_post_interval', 7)

    success = updateChannelDetails(channel_id, promo_post_time, int(promo_post_interval))
    if success:
        await bot.answer_callback_query(callback_query.id, "Details saved successfully!")
        await state.finish()  # End the state once the changes are saved
    else:
        await bot.answer_callback_query(callback_query.id, "Failed to save details. Please try again.")


@dp.callback_query_handler(lambda c: c.data.startswith("tags_"))
async def tags_handler(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[1])
    channel_name = callback_query.data.split("_")[2]
    callback_arguments = callback_query.data.split("_")
    if len(callback_arguments) > 3:
        action = callback_query.data.split("_")[3]
        tag = callback_query.data.split("_")[4]
        # Update the status of the clicked tag
        if action == "toggle":
            async with state.proxy() as data:
                tags = data["tags"]
                tags[tag] = not tags[tag]
    else:
        async with state.proxy() as data:
            tags = await get_channel_tags(channel_id)
            data["tags"] = tags

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
            tags = await get_channel_tags(channel_id)
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

    # update tags dict
    async with state.proxy() as data:
        data["tags"] = await get_channel_tags(channel_id)


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


@dp.callback_query_handler(lambda c: c.data.startswith("subscriptionchoice_"))
async def process_subscription_choice(callback_query: types.CallbackQuery, state: FSMContext):
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
            invoice_title = f"Make  {channel_name}"
            invoice_description = "Тестовое описание товара"
            invoice_payload = f"{channel_id}_{channel_name}_{selected_subscription['id']}_{selected_subscription['name']}"
            invoice_currency = "RUB"
            invoice_prices = [{"label": "Руб", "amount": selected_subscription['price'] * 100}]

            # Send a message with the cancel option and store its message ID
            cancel_button = InlineKeyboardButton("Cancel", callback_data="cancel_subscription")
            keyboard = InlineKeyboardMarkup()
            keyboard.add(cancel_button)

            # Send the invoice
            invoice_message = await bot.send_invoice(
                chat_id=callback_query.from_user.id,
                title=invoice_title,
                description=invoice_description,
                payload=invoice_payload,
                provider_token=YCASSATOKEN,
                currency=invoice_currency,
                start_parameter="test_bot",
                prices=invoice_prices
            )
            # Store the invoice message ID
            await state.update_data(invoice_msg_id=invoice_message.message_id)

            cancel_msg = await bot.send_message(
                chat_id=callback_query.from_user.id,
                text="Click 'Cancel' to stop the subscription process.",
                reply_markup=keyboard
            )

            # Store the message ID in user's state data
            await state.set_data({'cancel_msg_id': cancel_msg.message_id, 'invoice_msg_id': invoice_message.message_id})
        else:
            await callback_query.answer("Invalid subscription choice.")
    else:
        await callback_query.answer("Failed to retrieve subscription data from the API.")


# Handler for cancel subscription button
@dp.callback_query_handler(lambda c: c.data == "cancel_subscription")
async def process_cancel_subscription(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    # Retrieve message IDs from the state
    cancel_msg_id = user_data.get('cancel_msg_id')
    invoice_msg_id = user_data.get('invoice_msg_id')

    # Delete the cancel button message
    if cancel_msg_id:
        await bot.delete_message(chat_id=callback_query.from_user.id, message_id=cancel_msg_id)

    # Delete the invoice message
    if invoice_msg_id:
        await bot.delete_message(chat_id=callback_query.from_user.id, message_id=invoice_msg_id)

    # Finish the state
    await state.finish()


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
                duration = timedelta(seconds=time_left)
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
