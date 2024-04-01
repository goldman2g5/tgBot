import json
import logging
import time
from typing import List

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.responses import JSONResponse

# from notification_service import *
from bot import bot, dp
from states import *

# uvicorn main:app --reload

app = FastAPI()


def save_code(user_id: int, code: str):
    try:
        with open('codes.json', 'r+') as f:
            codes = json.load(f)
    except FileNotFoundError:
        codes = {}
    codes[str(user_id)] = code
    with open('codes.json', 'w') as f:
        json.dump(codes, f)


def get_code(user_id: int):
    try:
        with open('codes.json', 'r') as f:
            codes = json.load(f)
            return codes.pop(str(user_id), None), codes
    except FileNotFoundError:
        return None, {}


def encode_number_to_letters(number):
    """Encode a number to a string using a=1, b=2, ..., i=9, j=0."""
    encoded = ""
    for digit in str(number):
        if digit == "0":
            encoded += "j"  # 'j' represents 0
        else:
            encoded += chr(int(digit) + 96)  # 'a'=1,...,'i'=9
    return encoded


def decode_letters_to_number(encoded_string):
    """Decode a string back to numbers using a=1, b=2, ..., i=9, j=0."""
    decoded = ""
    for char in encoded_string:
        if char == "j":
            decoded += "0"  # Convert 'j' back to 0
        else:
            decoded += str(ord(char) - 96)  # Reverse the encoding process for 1-9
    return decoded


@app.get("/get_verification_code/{user_id}")
async def get_verification_code(user_id: int):
    verification_code, remaining_codes = get_code(user_id)
    if verification_code:
        # Save the remaining codes after removal
        with open('codes.json', 'w') as f:
            json.dump(remaining_codes, f)
        return {"user_id": user_id, "verification_code": verification_code}
    else:
        raise HTTPException(status_code=404, detail="Verification code not found or has already been retrieved.")


@dp.message_handler(Command("authclient"))
async def auth_client_command(message: types.Message):
    # Your existing logic here

    args = message.get_args().split()  # Assumes that the command format is "/authclient <code>"
    if not args:
        await message.answer("bebra bebra, `/authclient 4455`.")
        return

    verification_code = decode_letters_to_number(args[0])
    print(verification_code)
    # Assuming you have a mechanism to associate the code with a user/session:

    save_code(int(message.from_user.id), verification_code)
    print(f"auth_client_command {get_code(message.from_user.id)}")

    # Process the verification code here. For example, store it, verify it, etc.
    await message.answer(f"done")


@app.post("/trigger_verification/{user_id}")
async def trigger_verification(user_id: int):
    await bot.send_message(user_id, "a=1 b=2 c=3\nd=4 e=5 f=6\ng=7 h=8 i=9\nj=0\n/authclient (code)")
    return {"message": "Verification request sent."}


class NotificationModel(BaseModel):
    ChannelAccess: object
    ChannelName: str
    ChannelId: int
    UserId: int
    TelegramUserId: int
    TelegramChatId: int
    TelegamChannelId: int
    ContentType: str


@app.post("/send_notifications")
async def send_notifications(notifications: List[NotificationModel]):
    for notification in notifications:
        # Convert the Pydantic model to a dict to reuse the existing send_notification function
        await send_notification(notification.dict())
        time.sleep(1)
    return {"message": "Notifications sent successfully"}


# @app.post("/send_notifications")
# async def send_notifications(request: Request):
#     try:
#         # Parse request body manually
#         body = await request.json()
#         # Validate manually parsed data with Pydantic
#         notifications = [NotificationModel(**notif) for notif in body]
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=400, detail=f"JSON decoding error: {e.msg}")
#     except ValidationError as e:
#         raise HTTPException(status_code=422, detail=e.errors())
#
#     for notification in notifications:
#         await send_notification(notification.dict())
#         await asyncio.sleep(1)


@app.get("/")
async def root():
    return {"message": "working fine"}


class ChannelQuery(BaseModel):
    ChannelId: int
    NumberOfDays: int


# async def get_pyro_client():
#     # Initialize or ensure pyro_client is started
#     # This is just a placeholder. Adapt it to your actual pyro_client initialization logic.
#     if not pyro_client.is_connected:
#         await pyro_client.start()
#     return pyro_client


# @app.post("/get_daily_views/")
# async def get_daily_views(query: ChannelQuery, client=Depends(get_pyro_client)):
#     try:
#         chat = await client.get_chat(query.ChannelId)
#         chat_id = chat.id
#
#         messages = await get_messages_from_past_days(chat_id, query.NumberOfDays, start_date=None)
#         views_by_day = await calculate_daily_views(messages, query.NumberOfDays)
#
#         daily_stats = [
#             {"date": str(day), "views": data["views"], "lastMessageId": data["last_message_id"]}
#             for day, data in views_by_day.items()
#         ]
#
#         return json.loads(json.dumps(daily_stats))  # FastAPI will automatically convert dict to JSON
#
#     except Exception as e:
#         logging.error(f"An error occurred: {e}")
#         raise HTTPException(status_code=500, detail="An error occurred while processing your request.")


async def send_notification(notification):
    channel_name = notification.get('ChannelName', '')
    telegram_chat_id = notification.get('TelegramChatId', '')
    channel_id = notification.get('ChannelId', '')
    notification_type = notification.get('ContentType', '')  # Fetch the notification type from the JSON

    # Prepare a generic markup
    markup = types.InlineKeyboardMarkup(row_width=1)

    # Determine the type of notification and customize the message and markup accordingly
    if notification_type == 'bump':
        button_text = "Bump"
        message = f"Пришло время бампнуть {channel_name}!"
        callback_data = f"bump_{channel_id}_delete"
    elif notification_type == 'subscription':
        button_text = None  # No button needed for subscription expiration
        message = f"Подписка для {channel_name} истекла!"
    elif notification_type == 'promo':
        button_text = "Promo"
        message = "Пришло время для промо-поста!"
        callback_data = f"promo_{channel_id}_delete"
    else:
        print(f"Unsupported notification type: {notification_type}")
        return  # Early exit for unsupported notification types

    # Add button to markup if needed
    if button_text:
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    # Send the notification
    await bot.send_message(telegram_chat_id, message, reply_markup=(markup if button_text else None))
