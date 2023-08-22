import base64
import io
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import save_channel_information, save_channel_access, get_channel_id_from_database, get_user_id_from_database
from bot import dp, bot
from misc import check_bot_in_channel, open_menu
from states import AddChannelStates

import base64
import io
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api import save_channel_information, save_channel_access, get_channel_id_from_database, get_user_id_from_database
from bot import dp, bot
from misc import check_bot_in_channel, open_menu
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
    await callback_query.answer("Adding channel cancelled.")
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="cancel_add_channel")
async def cancel_add_channel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await cancel_add_channel(callback_query, state)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_channel_description, text="cancel_enter_description")
async def cancel_enter_description_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await cancel_add_channel(callback_query, state)


@dp.callback_query_handler(state=AddChannelStates.waiting_for_channel_name, text="cancel_enter_channel_name")
async def cancel_enter_channel_name_handler(callback_query: types.CallbackQuery, state: FSMContext):
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
        await message.answer("Error: Invalid channel name format.")
        return

    # Save the channel name in the context
    await state.update_data(channel_name=channel_name)
    await state.update_data(message_ids=[])

    await update_message_ids(state, message.message_id)
    await update_message_ids(state, channel_name_message_id)

    # Retrieve the channel ID using bot.get_chat
    try:
        print(channel_name)
        chat = await bot.get_chat(channel_name)
        channel_id = chat.id
        # Store the channel_id in the state
        await state.update_data(channel_id=channel_id, user_id=message.from_user.id)
    except Exception as e:
        await message.answer(f"Error: Failed to retrieve the channel ID: {e}")
        await state.finish()
        return

    # Create the "Add Bot" button and send the message
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Check", callback_data="add_bot"))
    markup.add(InlineKeyboardButton("Cancel", callback_data="cancel_add_channel"))  # Add cancel button
    await message.answer("To add a channel for monitoring, you need to add the bot to the channel.",
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
    channel_id = data.get("channel_id")
    user = callback_query.from_user

    if not await check_bot_in_channel(channel_name):
        return "Error: Bot was not added to the channel."

    if not await is_user_admin(channel_name, user.id):
        return "Error: You are not an administrator of the specified channel."

    await state.update_data(channel_name=channel_name, user_id=user.id, channel_id=channel_id)
    sent_message = await callback_query.message.answer(
        "Please enter the channel description:",
        reply_markup=InlineKeyboardMarkup(row_width=1)
        .add(InlineKeyboardButton("Cancel", callback_data="cancel_enter_description"))
    )

    await update_message_ids(state, callback_query.message.message_id)
    await update_message_ids(state, sent_message.message_id)
    await AddChannelStates.waiting_for_channel_description.set()

    return "Success! Bot added to the channel."


@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="add_bot")
async def process_add_bot(callback_query: types.CallbackQuery, state: FSMContext):
    message = await process_add_bot_core(callback_query, state)
    await callback_query.answer(message)


async def process_channel_description_core(message, state):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    user_id = data.get("user_id")

    if channel_name is None:
        await message.answer("Error: Failed to get channel information.")
        await state.finish()
        return

    channel_description = message.text
    if len(channel_description) > 130:
        error_msg = await message.answer("Error: Description must be 130 symbols or shorter. Please enter it again.")
        await update_message_ids(state, error_msg.message_id)
        return  # Return early so user can re-enter

    await state.update_data(channel_description=channel_description)


@dp.message_handler(state=AddChannelStates.waiting_for_channel_description)
async def process_channel_description(message: types.Message, state: FSMContext):
    await process_channel_description_core(message, state)

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Русский", callback_data="language_ru"),
        InlineKeyboardButton("Английский", callback_data="language_en"),
        InlineKeyboardButton("Украинский", callback_data="language_uk")
    )
    await message.answer("Выберете язык вашего канала", reply_markup=markup)
    await AddChannelStates.waiting_for_language_selection.set()


@dp.callback_query_handler(state=AddChannelStates.waiting_for_language_selection)
async def process_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    chosen_language = callback_query.data.split("_")[1]
    await state.update_data(language=chosen_language)

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🇷🇺", callback_data="flag_ru"),
        InlineKeyboardButton("🇬🇧", callback_data="flag_en"),
        InlineKeyboardButton("🇺🇦", callback_data="flag_uk")
    )
    await callback_query.message.answer("Выберете флаг вашего канала", reply_markup=markup)
    await AddChannelStates.waiting_for_flag_selection.set()


@dp.callback_query_handler(state=AddChannelStates.waiting_for_flag_selection)
async def process_flag_selection(callback_query: types.CallbackQuery, state: FSMContext):
    chosen_flag = callback_query.data.split("_")[1]
    data = await state.get_data()

    chosen_language = data.get("language")
    channel_description = data.get("channel_description")
    channel_name = data.get("channel_name")
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    chat = await bot.get_chat(channel_name)
    members_count = await bot.get_chat_members_count(chat.id)
    avatar_base64 = await get_channel_avatar(chat)

    # Save all details now
    db_user_id = await get_user_id_from_database(user_id)
    if db_user_id is None:
        await callback_query.message.answer("Error: Failed to get user information.")
        await state.finish()
        return

    channel_id = await save_channel_information(
        channel_name, channel_description, members_count, avatar_base64, user_id, channel_id, chosen_language, chosen_flag
    )

    if channel_id == 0:
        await callback_query.message.answer("Failed to save channel information.")
        await state.finish()
        return

    if not await save_channel_access(db_user_id, channel_id):
        await callback_query.message.answer("Failed to save channel access.")
        await state.finish()
        return

    sent_message = await callback_query.message.answer("Channel information saved successfully.")
    await update_message_ids(state, callback_query.message.message_id)
    await update_message_ids(state, sent_message.message_id)
    data = await state.get_data()
    await delete_messages(bot, callback_query.message.chat.id, data.get("message_ids", []))
    await open_menu(callback_query.message.chat.id, callback_query.message.message_id)
    await state.finish()
