import base64
import urllib
from asyncio import exceptions
from urllib import parse
from urllib.parse import parse_qs

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, state
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from api import *
from bot import dp, bot
from misc import open_menu
from states import AddChannelStates
from api import API_URL, default_headers


def send_message(connection_id, username, user_id):
    url = f"{API_URL}/Auth"
    payload = {
        "Username": username,
        "UserId": str(user_id),
        "Unique_key": ""
    }

    params = {
        "connectionId": connection_id
    }

    response = requests.post(url, json=payload, params=params, verify=False, headers=default_headers)

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message")
        print(response.text)
        print(response.json())


def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')


async def handle_payment(user_id, payment_data):
    pass


@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        await message.delete_reply_markup()
    except:
        pass
    username = message.from_user.username
    user_id = message.from_user.id
    args = message.get_args()

    # Downloading the user's avatar
    avatar_bytes = None  # Default to None in case no profile photo is found
    profile_photos = await bot.get_user_profile_photos(user_id, limit=1)

    if args.startswith("pay"):
        payment_id = args[3:]  # Extracting the payment ID
        real_payment_data = await get_payment_data(payment_id)

        if real_payment_data is None or isinstance(real_payment_data, str):
            await message.reply("Payment data not found or an error occurred.")
            return

        # Call the start_payment_process function with real data
        await start_payment_process(message, real_payment_data, state)
        return  # Stop further processing after handling the payment

    if profile_photos.photos:  # Check if the user has a profile photo
        photo = profile_photos.photos[0][0]  # latest photo, smallest size
        file = await bot.get_file(photo.file_id)
        file_path = file.file_path
        url = f"https://api.telegram.org/file/bot6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4/{file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                avatar_bytes = await response.read()  # byte array of the photo

    # Save user info
    avatar_str = bytes_to_base64(avatar_bytes) if avatar_bytes else None
    save_user_info(user_id, message.chat.id, username, avatar_str)

    if args:
        connection_id = args
        send_message(connection_id, username, user_id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅", callback_data="remove_authorize_msg"))
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.send_message(message.chat.id, "Вы успешно авторизовались, возвращайтесь на сайт.",
                               reply_markup=markup)
        return

    markup = InlineKeyboardMarkup(row_width=1)
    # TODO: translate
    markup.add(InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               InlineKeyboardButton("Управление каналами", callback_data="manage_channels"),
               InlineKeyboardButton("Настройка уведомлений", callback_data="xxx_notifications_settings"))

    await bot.send_message(message.chat.id, "Меню:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "remove_authorize_msg")
async def remove_authorize_msg_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


YCASSATOKEN = "381764678:TEST:59527"


async def start_payment_process(message: types.Message, payment_data: dict, state: FSMContext):
    subscriptions = get_subscriptions_from_api()
    if subscriptions is not None:
        selected_subscription = next(
            (sub for sub in subscriptions if sub['id'] == payment_data["subscriptionTypeId"]), None)
        if selected_subscription:
            invoice_title = f"Subscription for {payment_data['channelName']}"
            invoice_description = f"{selected_subscription['name']} subscription"
            invoice_payload = f"{payment_data['channelId']}_{payment_data['channelName']}_{selected_subscription['id']}_{selected_subscription['name']}"
            invoice_currency = "RUB"
            price_amount = selected_subscription['price'] - (
                    selected_subscription['price'] * payment_data.get('discount', 0) / 100)
            invoice_prices = [LabeledPrice(label="RUB", amount=int(price_amount * 100))]

            invoice_message = await bot.send_invoice(
                chat_id=message.from_user.id,
                title=invoice_title,
                description=invoice_description,
                payload=invoice_payload,
                provider_token=YCASSATOKEN,
                currency=invoice_currency,
                start_parameter="subscribe",
                prices=invoice_prices
            )

            await state.update_data(invoice_msg_id=invoice_message.message_id)
        else:
            await message.reply("Invalid subscription choice.")
    else:
        await message.reply("Failed to retrieve subscription data from the API.")


@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Open the main menu
    markup = InlineKeyboardMarkup(row_width=1)
    # TODO: translate
    markup.add(InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               InlineKeyboardButton("Управление каналами", callback_data="manage_channels"),
               InlineKeyboardButton("Настройка уведомлений", callback_data="xxx_notifications_settings"))

    if callback_query.message.reply_markup:
        # Edit the existing message with the updated inline keyboard
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup,
            text=f"Меню:",
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer(text="Меню:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def add_channel_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Set the state
    await AddChannelStates.waiting_for_channel_name.set()
    # TODO: translate
    message = await callback_query.message.answer("Введите ссылку на канал:",
                                                  reply_markup=InlineKeyboardMarkup(row_width=1)
                                                  .add(InlineKeyboardButton("Отмена",
                                                                            callback_data="cancel_enter_channel_name")))
    await dp.current_state().update_data(channel_name_message_id=message.message_id)


@dp.callback_query_handler(lambda c: c.data == "manage_channels")
async def manage_channels_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()
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
        markup.add(InlineKeyboardButton("В главное меню", callback_data="back_to_menu"))
        if callback_query.message.reply_markup:
            # Edit the existing message with the updated inline keyboard
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=markup,
                text=f"Ваши каналы:",
            )
        else:
            # Send a new message with the inline keyboard
            await callback_query.message.answer(text="Ваши каналы:", reply_markup=markup)
    else:
        await callback_query.message.answer("У вас нет каналов.")
