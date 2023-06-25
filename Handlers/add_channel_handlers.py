import base64
import io
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


# Handler for entering the channel name
@dp.message_handler(state=AddChannelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    channel_name = "@" + message.text

    # Save the channel name in the context
    await state.update_data(channel_name=channel_name)
    await state.update_data(message_ids=[])

    # Retrieve the channel ID using bot.get_chat
    try:
        chat = await bot.get_chat(channel_name)
        channel_id = chat.id
        # Store the channel_id in the state
        await state.update_data(channel_id=channel_id, user_id=message.from_user.id)
    except Exception as e:
        await message.answer(f"Error: Failed to retrieve the channel ID: {e}")
        return

    # Create the "Add Bot" button and send the message
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Check", callback_data="add_bot"))
    await message.answer("To add a channel for monitoring, "
                         "you need to add the bot to the channel.", reply_markup=markup)

    # Add the message ID to the list
    await state.update_data(message_ids=[message.message_id])

    await AddChannelStates.waiting_for_check.set()


# Handler for the "Add Bot" button
@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="add_bot")
async def process_add_bot(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    channel_id = data.get("channel_id")  # Retrieve the channel_id from the state

    user = callback_query.from_user

    # Check if the bot is added to the channel
    if await check_bot_in_channel(channel_name):
        # Check if the user is an administrator of the channel
        try:
            chat = await bot.get_chat(channel_name)
            member = await bot.get_chat_member(chat.id, user.id)
            if member.status in ("administrator", "creator"):
                # Store channel_name, user_id, and channel_id in the state
                await state.update_data(channel_name=channel_name, user_id=user.id, channel_id=channel_id)
                await callback_query.answer("Success! Bot added to the channel.")

                sent_message = await callback_query.message.answer("Please enter the channel description:")

                # Get the message IDs from the state
                data = await state.get_data()
                message_ids = data.get("message_ids", [])

                # Add the message IDs to the list
                message_ids.append(callback_query.message.message_id)
                message_ids.append(sent_message.message_id)

                # Save the updated message IDs list in the state
                await state.update_data(message_ids=message_ids)

                await AddChannelStates.waiting_for_channel_description.set()
                return
            else:
                message = "Error: You are not an administrator of the specified channel."
        except Exception as e:
            message = f"Error occurred during verification: {e}"
    else:
        message = "Error: Bot was not added to the channel."

    await callback_query.answer(message)


# Handler for entering the channel description
@dp.message_handler(state=AddChannelStates.waiting_for_channel_description)
async def process_channel_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_name = data.get("channel_name")
    user_id = data.get("user_id")  # Retrieve the user's ID from the state
    channel_id = data.get("channel_id")  # Retrieve the channel_id from the state

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

    # Retrieve user_id from the database
    db_user_id = await get_user_id_from_database(user_id)

    if db_user_id is None:
        await message.answer("Error: Failed to get user information.")
        await state.finish()
        return

    # Save channel information to the database and get the channel ID
    channel_id = await save_channel_information(
        channel_name, channel_description, members_count, avatar_base64, user_id, channel_id
    )

    if channel_id == 0:
        await message.answer("Failed to save channel information.")
        await state.finish()
        return

    # Save channel access
    channel_access_saved = await save_channel_access(db_user_id, channel_id)

    if channel_access_saved:
        sent_message = await message.answer("Channel information and access saved successfully.")
    else:
        sent_message = await message.answer("Failed to save channel access.")

    # Get the message IDs from the state
    data = await state.get_data()
    message_ids = data.get("message_ids", [])

    # Add the message IDs to the list
    message_ids.append(message.message_id)
    message_ids.append(sent_message.message_id)

    # Save the updated message IDs list in the state
    await state.update_data(message_ids=message_ids)

    # Get the message IDs from the state
    message_ids = data.get("message_ids", [])

    # Add the current message ID to the list
    message_ids.append(message.message_id)

    # Delete the messages
    for msg_id in message_ids:
        try:
            await bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            print(f"Error deleting message {msg_id}: {e}")

    await open_menu(message.chat.id, message.message_id)

    await state.finish()
