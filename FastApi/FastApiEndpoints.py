import json
import logging

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from bot import pyro_client
from Websocket.SocketFunctions import get_messages_from_past_days, calculate_daily_views

from notification_service import *

# uvicorn main:app --reload

app = FastAPI()


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

async def get_pyro_client():
    # Initialize or ensure pyro_client is started
    # This is just a placeholder. Adapt it to your actual pyro_client initialization logic.
    if not pyro_client.is_connected:
        await pyro_client.start()
    return pyro_client

@app.post("/get_daily_views/")
async def get_daily_views(query: ChannelQuery, client=Depends(get_pyro_client)):
    try:
        chat = await client.get_chat(query.ChannelId)
        chat_id = chat.id

        messages = await get_messages_from_past_days(chat_id, query.NumberOfDays, start_date=None)
        views_by_day = await calculate_daily_views(messages, query.NumberOfDays)

        daily_stats = [
            {"date": str(day), "views": data["views"], "lastMessageId": data["last_message_id"]}
            for day, data in views_by_day.items()
        ]

        return json.loads(json.dumps(daily_stats))  # FastAPI will automatically convert dict to JSON

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.")


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
