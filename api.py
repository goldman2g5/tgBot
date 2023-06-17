from typing import List
import aiohttp
import requests


# Function to save user info in the database
def save_user_info(user_id, chat_id):
    user = {
        "TelegramId": user_id,
        "ChatId": chat_id
    }
    response = requests.post("http://localhost:8053/Api/User", json=user)


async def save_channel_information(channel_name: str, channel_description: str, members_count: int, avatar_base64: str,
                                   user_id: int, channel_id: int) -> int:
    # Write channel information to the database using the API
    api_url = "http://localhost:8053/api/Channel"
    print(user_id)

    data = {
        "id": 0,
        "name": channel_name,
        "description": channel_description,
        "members": members_count,
        "avatar": avatar_base64,
        "user": user_id,
        "telegram_id": channel_id
    }

    response = requests.post(api_url, json=data)
    if response.status_code == 201:
        return response.json().get("id")
    else:
        return 0


async def save_channel_access(user_id, channel_id):
    api_url = "http://localhost:8053/Api/ChannelAccess"

    data = {
        "userId": user_id,
        "channelId": int(channel_id) if channel_id is not None else None
    }

    response = requests.post(api_url, json=data)
    if response.status_code == 201:
        return True
    else:
        return False


# Function to retrieve user's channels from the API
def get_user_channels(user_id: int) -> List[dict]:
    api_url = f"http://localhost:8053/api/Channel/ByUser/{user_id}"
    response = requests.get(api_url)
    print(response.status_code)
    print(response.text)
    print(user_id)
    if response.status_code == 200:
        return response.json()
    else:
        return []


# Retrieve the current notification status from the API
def get_notification_status(channel_id):
    api_url = f"http://localhost:8053/api/Channel/{channel_id}"
    response = requests.get(api_url)
    if response.status_code == 404:
        return None  # Channel not found

    channel_data = response.json()
    notifications_enabled = channel_data.get("notifications")

    if notifications_enabled is None:
        notifications_enabled = False  # Assume notifications are disabled if the value is null

    return notifications_enabled


# Toggle the notification status in the API
def toggle_notification_status(channel_id, new_notifications_enabled):
    api_toggle_url = f"http://localhost:8053/api/Channel/ToggleNotifications/{channel_id}"
    put_data = {"notifications": new_notifications_enabled}
    response = requests.put(api_toggle_url, json=put_data)
    return response.status_code == 204


# Process channel bump
async def bump_channel(channel_id: int):
    api_url = "http://localhost:8053/api/Channel/Bump/" + str(channel_id)

    try:
        response = requests.post(api_url)
        return response
    except requests.exceptions.RequestException as e:
        # Handle exception (e.g., connection error)
        print("Error:", e)
        return None


# Function to retrieve the user ID from the database
async def get_user_id_from_database(user_id: int):
    try:
        # Make a GET request to the API endpoint for retrieving user by Telegram ID
        response = requests.get(f"http://localhost:8053/api/User/ByTelegramId/{user_id}")
        if response.status_code == 200:
            user_data = response.json()
            if user_data:
                return user_data["id"]  # Assuming the response contains a single user object and you want the ID
            else:
                return None
        else:
            print(f"Error retrieving user ID from the database. Status code: {response.text}")
            return None
    except Exception as e:
        print(f"Error retrieving user ID from the database: {e}")
        return None


# Function to retrieve the channel ID from the database
async def get_channel_id_from_database(channel_id: int):
    try:
        # Make a GET request to the API endpoint for retrieving channel by Telegram ID
        response = requests.get(f"http://localhost:8053/api/Channel/ByTelegramId/{channel_id}")
        if response.status_code == 200:
            channel_data = response.json()
            if channel_data:
                return channel_data["id"]  # Assuming the response contains a single channel object and you want the ID
            else:
                return None
        else:
            print(f"Error retrieving channel ID from the database. Status code: {response.text}")
            return None
    except Exception as e:
        print(f"Error retrieving channel ID from the database: {e}")
        return None
