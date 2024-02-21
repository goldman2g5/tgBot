import base64
import random
import io

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from api import get_user_id_from_database, save_channel_information, save_channel_access, channel_exists, \
    get_channel_by_id
from bot import dp, bot


class ChannelCreationStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_bot_in_channel = State()
    waiting_for_description = State()
    waiting_for_region = State()


async def bot_status(channel_id: int) -> str:
    try:
        chat = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status == "administrator":
            return 'admin'
    except Exception as e:
        print(e)
    return 'error'


async def get_channel_avatar(chat):
    if not chat.photo:
        return None

    avatar = chat.photo
    avatar_file = io.BytesIO()
    await avatar.download_small(destination=avatar_file)
    avatar_bytes = avatar_file.getvalue()

    return base64.b64encode(avatar_bytes).decode()


@dp.callback_query_handler(lambda call: call.data == 'cancel_adding_channel', state='*')
async def cancel_adding_channel(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.delete_reply_markup()
    await callback.message.delete()

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               types.InlineKeyboardButton("Управление каналами", callback_data="manage_channels"),
               types.InlineKeyboardButton("Настройка уведомлений", callback_data="xxx_notifications_settings"))

    await bot.send_message(callback.message.chat.id, "Меню:", reply_markup=markup)


@dp.message_handler(state=ChannelCreationStates.waiting_for_channel, text='Отмена')
async def cancel_adding_channel(message: types.Message, state: FSMContext):
    await message.delete()
    async with state.proxy() as data:
        msgs_to_delete = data['msgs_to_delete']
    await state.finish()
    for msg_id in msgs_to_delete:
        await bot.delete_message(message.chat.id, msg_id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               types.InlineKeyboardButton("Управление каналами", callback_data="manage_channels"),
               types.InlineKeyboardButton("Настройка уведомлений", callback_data="xxx_notifications_settings"))

    await bot.send_message(message.chat.id, "Меню:", reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == 'add_channel')
async def add_channel_link(callback: types.CallbackQuery, state: FSMContext):
    await ChannelCreationStates.waiting_for_channel.set()

    req_id = random.randint(100000, 999999)
    administrator_rights = types.ChatAdministratorRights(can_manage_chat=True)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    req_criteria = types.KeyboardButtonRequestChat(request_id=req_id, chat_is_channel=True,
                                                   user_administrator_rights=administrator_rights)
    req_button = types.KeyboardButton("Выбрать канал", request_chat=req_criteria)
    keyboard.add(req_button)
    keyboard.add(types.KeyboardButton("Отмена"))

    await callback.message.delete()
    msg = await callback.message.answer("<b>Нажмите на кнопку ниже и выберите канал, который хотите добавить.</b>",
                                        reply_markup=keyboard)

    await state.update_data(msgs_to_delete=[msg.message_id])


@dp.message_handler(state=ChannelCreationStates.waiting_for_channel, content_types=types.ContentTypes.CHAT_SHARED)
async def test(message: types.Message, state: FSMContext):

    await ChannelCreationStates.waiting_for_bot_in_channel.set()
    async with state.proxy() as data:
        msgs_to_delete = data['msgs_to_delete']
    for msg_id in msgs_to_delete:
        await bot.delete_message(message.chat.id, msg_id)

    channel_id = message.chat_shared['chat_id']

    async with state.proxy() as data:
        data['channel_id'] = channel_id

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Проверить', callback_data='check_bot_in_channel'))
    keyboard.add(types.InlineKeyboardButton('Отмена', callback_data='cancel_adding_channel'))

    await message.answer(
        f'<b>Чтобы добавить канал на сервис, вам нужно пригласить бота в канал</b>',
        reply_markup=keyboard)


@dp.callback_query_handler(state=ChannelCreationStates.waiting_for_bot_in_channel)
async def check_bot_in_channel(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        channel_id = data['channel_id']

    status = await bot_status(channel_id)
    if status == 'admin':
        if await channel_exists(await (await bot.get_chat(channel_id)).get_url()):
            await callback.answer('Канал уже существует на сервисе, добавте другой.')
            return
        await ChannelCreationStates.waiting_for_description.set()

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('Отмена', callback_data='cancel_adding_channel'))

        msg = await callback.message.edit_text('Введите описание для вашего канала:', reply_markup=keyboard)

        async with state.proxy() as data:
            data['msgs_to_delete'] = [msg.message_id]
    else:
        await callback.answer(
            'Вы не добавили бота в канал, либо произошла ошибка. Попробуйте снова.',
            show_alert=True)


@dp.message_handler(state=ChannelCreationStates.waiting_for_description)
async def add_channel_description(message: types.Message, state: FSMContext):
    await ChannelCreationStates.waiting_for_region.set()
    await message.delete()

    async with state.proxy() as data:
        data['description'] = message.text
        msgs_to_delete = data['msgs_to_delete']

    for msg_id in msgs_to_delete:
        await bot.delete_message(message.chat.id, msg_id)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('RU', callback_data='ru'))
    keyboard.add(types.InlineKeyboardButton('EN', callback_data='en'))
    keyboard.add(types.InlineKeyboardButton('UA', callback_data='ua'))
    keyboard.add(types.InlineKeyboardButton('Отмена', callback_data='cancel_adding_channel'))

    msg = await message.answer('Выберите регион, в котором будет показываться ваш канал:',
                               reply_markup=keyboard)

    async with state.proxy() as data:
        data['msgs_to_delete'] = [msg.message_id]


@dp.callback_query_handler(state=ChannelCreationStates.waiting_for_region)
async def add_channel_region(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        msgs_to_delete = data['msgs_to_delete']
        channel_id = data['channel_id']
        channel_description = data['description']

    channel = await bot.get_chat(channel_id)
    channel_region = callback.data
    channel_name = channel.title
    user_id = callback.from_user.id
    channel_url = await channel.get_url()
    members_count = await channel.get_members_count()
    avatar = await get_channel_avatar(channel)

    db_user_id = await get_user_id_from_database(user_id)
    if not db_user_id:
        await callback.answer("Ошибка при получении информации о пользователе.", show_alert=True)
        await state.finish()
        return

    channel_id = await save_channel_information(
        channel_name, channel_description, members_count, avatar, user_id, channel_id, channel_region,
        channel_region, channel_url
    )

    if channel_id == 0:
        await callback.answer("Ошибка при сохранении информации о канале.", show_alert=True)
        await state.finish()
        return

    if not await save_channel_access(db_user_id, channel_id):
        await callback.answer("Ошибка при сохранении информации о доступе к каналу.", show_alert=True)
        await state.finish()
        return

    await callback.answer(f"Канал {channel_name} успешно добавлен на сервис!", show_alert=True)

    for msg_id in msgs_to_delete:
        await bot.delete_message(callback.message.chat.id, msg_id)

    await state.finish()

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               types.InlineKeyboardButton("Управление каналами", callback_data="manage_channels"),
               types.InlineKeyboardButton("Настройка уведомлений", callback_data="xxx_notifications_settings"))

    await bot.send_message(callback.message.chat.id, "Меню:", reply_markup=markup)
