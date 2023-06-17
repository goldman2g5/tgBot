from typing import List

import requests


# Function to save channel information to the database
async def save_channel_information(channel_name: str, channel_description: str, members_count: int, avatar_base64: str,
                                   user_id: int) -> bool:
    # Write channel information to the database using the API
    api_url = "http://localhost:8053/api/Channel"
    print(user_id)

    data = {
        "id": 0,
        "name": channel_name,
        "description": channel_description,
        "members": members_count,
        "avatar": avatar_base64,
        "user": user_id
    }

    response = requests.post(api_url, json=data)
    print(response.text)
    if response.status_code == 201:
        return True
    else:
        return False


# Function to retrieve user's channels from the API
def get_user_channels(user_id: int) -> List[dict]:
    api_url = f"http://localhost:8053/api/Channel/ByUser/{user_id}"
    response = requests.get(api_url)
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
