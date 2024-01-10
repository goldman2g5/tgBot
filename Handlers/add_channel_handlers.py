import base64
import io
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from api import save_channel_information, save_channel_access, get_user_id_from_database
from bot import dp, bot
from misc import check_bot_in_channel
from states import AddChannelStates


async def update_message_ids(state: FSMContext, message_id: int):
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(message_id)
    await state.update_data(message_ids=message_ids)


async def delete_messages(bot, chat_id, message_ids):
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id}: {e}")


async def cancel_add_channel(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await delete_messages(bot, callback_query.message.chat.id, data.get("message_ids", []))
    await state.finish()
    # TODO: translate
    await callback_query.answer("Добавление канала отменено.")
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="cancel_add_channel")
async def cancel_add_channel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await cancel_add_channel(callback_query, state)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_channel_description, text="cancel_enter_description")
async def cancel_enter_description_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await cancel_add_channel(callback_query, state)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_channel_name, text="cancel_enter_channel_name")
async def cancel_enter_channel_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await cancel_add_channel(callback_query, state)


@dp.message_handler(state=AddChannelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_name_message_id = data.get("channel_name_message_id")
    channel_name_input = message.text.strip()

    # Regular expression pattern to match the different formats of channel names
    channel_name_pattern = r"(?:https?://t\.me/|t\.me/|@)?([^/\s]+)"
    match = re.match(channel_name_pattern, channel_name_input)
    if match:
        channel_name = "@" + match.group(1)
    else:
        # TODO: translate
        await message.answer("Ошибка, неправильная ссылка на канал.")
        return

    # Save the channel name in the context
    await state.update_data(channel_name=channel_name)
    await state.update_data(message_ids=[])

    await update_message_ids(state, message.message_id)
    await update_message_ids(state, channel_name_message_id)

    # Create the "Add Bot" button and send the message
    markup = InlineKeyboardMarkup(row_width=1)
    # TODO: translate
    markup.add(InlineKeyboardButton("Проверить", callback_data="add_bot"))
    markup.add(InlineKeyboardButton("Отменить", callback_data="cancel_add_channel"))  # Add cancel button
    await message.answer("Чтобы добавить канал на сервис, вам нужно пригласить бота в канал.",
                         reply_markup=markup)

    await update_message_ids(state, message.message_id)

    await AddChannelStates.waiting_for_check.set()


async def is_user_admin(channel_name, user_id):
    try:
        chat = await bot.get_chat(channel_name)
        member = await bot.get_chat_member(chat.id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def get_channel_avatar(chat):
    if not chat.photo:
        return None

    avatar = chat.photo
    avatar_file = io.BytesIO()
    await avatar.download_small(destination=avatar_file)
    avatar_bytes = avatar_file.getvalue()

    return base64.b64encode(avatar_bytes).decode()


async def process_add_bot_core(callback_query, state):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    channel_name_real = data.get("channel_name_real")
    channel_id = data.get("channel_id")
    user = callback_query.from_user

    # TODO: translate
    if not await check_bot_in_channel(channel_name):
        return "Ошибка: Бот не был добавлен в канал."

    if not await is_user_admin(channel_name, user.id):
        return "Ошибка, вы не администратор данного канала."

        # Retrieve the channel ID using bot.get_chat



    await state.update_data(channel_name=channel_name, user_id=user.id, channel_id=channel_id,
                            channel_name_real=channel_name_real)
    sent_message = await callback_query.message.edit_text(
        "Введите описание для вашего канала:",
        reply_markup=InlineKeyboardMarkup(row_width=1)
        .add(InlineKeyboardButton("Отмена", callback_data="cancel_enter_description"))
    )

    await update_message_ids(state, callback_query.message.message_id)
    await update_message_ids(state, sent_message.message_id)
    await AddChannelStates.waiting_for_channel_description.set()

    return "Бот успешно добавлен в канал!."


@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="add_bot")
async def process_add_bot(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    message = await process_add_bot_core(callback_query, state)
    await callback_query.answer(message)


async def process_channel_description_core(message, state):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    user_id = data.get("user_id")

    if channel_name is None:
        # TODO: translate
        await message.answer("Ошибка при получении информации о канале.")
        await state.finish()
        return

    channel_description = message.text
    if len(channel_description) > 130:
        error_msg = await message.answer("Ошибка: Длинна описания должна быть меньше 130 симыволов.")
        await update_message_ids(state, error_msg.message_id)
        return  # Return early so user can re-enter

    await state.update_data(channel_description=channel_description)


@dp.message_handler(state=AddChannelStates.waiting_for_channel_description)
async def process_channel_description(message: types.Message, state: FSMContext):
    await process_channel_description_core(message, state)

    data = await state.get_data()
    channel_name = data.get("channel_name")
    try:
        chat = await bot.get_chat(channel_name)
        channel_id = chat.id

        # Check if the channel is public to construct the URL
        if chat.username:
            channel_url = f"https://t.me/{chat.username}"
        else:
            channel_url = "Private Channel"  # Handle private channels differently as they don't have URLs

        # Store the channel_id and channel_url in the state
        await state.update_data(channel_id=channel_id, user_id=message.from_user.id,
                                channel_name_real=chat.full_name, channel_url=channel_url)
    except Exception as e:
        # TODO: translate
        await message.answer(f"Ошибка при получении информаци о канале: {e}")
        await state.finish()
        return

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("RU", callback_data="language_ru"),
        InlineKeyboardButton("EU", callback_data="language_en"),
        InlineKeyboardButton("UA", callback_data="language_uk")
    )
    # TODO: translate
    sent_message = await message.answer("Выберите регион", reply_markup=markup)
    await update_message_ids(state, message.message_id)
    await update_message_ids(state, sent_message.message_id)
    await AddChannelStates.waiting_for_language_selection.set()


@dp.callback_query_handler(state=AddChannelStates.waiting_for_language_selection)
async def process_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    chosen_language = callback_query.data.split("_")[1]
    await state.update_data(language=chosen_language)

    chosen_flag = "undefined"
    data = await state.get_data()

    chosen_language = data.get("language")
    channel_description = data.get("channel_description")
    channel_name = data.get("channel_name")
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    channel_name_real = data.get("channel_name_real")
    channel_url = data.get("channel_url")
    chat = await bot.get_chat(channel_name)
    members_count = await bot.get_chat_members_count(chat.id)
    avatar_base64 = await get_channel_avatar(chat)

    # Save all details now
    db_user_id = await get_user_id_from_database(user_id)
    if db_user_id is None:
        # TODO: translate
        await callback_query.message.answer("Ошибка при получении информации о пользователе.")
        await state.finish()
        return

    channel_id = await save_channel_information(
        channel_name_real, channel_description, members_count, avatar_base64, user_id, channel_id, chosen_language,
        chosen_flag, channel_url
    )

    if channel_id == 0:
        # TODO: translate
        await callback_query.message.answer("Ошибка при сохранении информации о канале.")
        await state.finish()
        return

    if not await save_channel_access(db_user_id, channel_id):
        # TODO: translate
        await callback_query.message.answer("Ошибка при сохранении информации о доступе к каналу.")
        await state.finish()
        return

    # TODO: translate
    sent_message = await callback_query.message.answer("Информация о канале успешно добавлена.")
    await update_message_ids(state, callback_query.message.message_id)
    await update_message_ids(state, sent_message.message_id)
    data = await state.get_data()
    await delete_messages(bot, callback_query.message.chat.id, data.get("message_ids", []))
    # await open_menu(callback_query.message.chat.id, callback_query.message.message_id)
    await state.finish()
