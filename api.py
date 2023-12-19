import json
import logging
from typing import List
import aiohttp
import requests

# API_URL = "http://localhost:7256/api"
API_URL = "https://tgsearch.info:1488/api"
API_KEY = "7bdf1ca44d84484c9864c06c0aedc1beb740909b02e4404ebafd381db897e1a5387567f8b42f47c7b5192eac60547460e0003c11fd804d1a966a30eacd939a3acaa9a352797f436aad6cd14f27517554"
Verify_value = False

default_headers = {"X-API-KEY": API_KEY}

# Configure logging settings
logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w",
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define a logger object specific to the module
logger = logging.getLogger(__name__)


# Function to save user info in the database
def save_user_info(user_id: int, chat_id: int, username: str, avatar: str):
    user = {
        "telegramId": user_id,
        "chatId": chat_id,
        "username": username,
        "avatar": avatar
    }

    response = requests.post(f"{API_URL}/User", json=user, verify=Verify_value, headers=default_headers)

    if response.status_code != 201:
        logger.critical(f"Failed to save user info\nTelegramId: {user_id}\nChatId: {chat_id}\n{response.text}")


async def save_channel_information(channel_name: str, channel_description: str, members_count: int, avatar_base64: str,
                                   user_id: int, channel_id: int, language: str, flag: str, channel_url: str) -> int:
    # Write channel information to the database using the API
    api_url = f"{API_URL}/Channel"
    print(f"channel id - {channel_id}")
    data = {
        "id": 0,
        "name": channel_name,
        "description": channel_description,
        "members": members_count,
        "avatar": avatar_base64,
        "user": user_id,
        "telegramId": channel_id,
        "language": language,
        "flag": flag,
        "url": channel_url
    }

    response = requests.post(api_url, json=data, verify=Verify_value, headers=default_headers)
    if response.status_code == 201:
        return response.json().get("id")
    else:
        logger.critical(
            f"Failed to save channel info\nchannel_name - {channel_name}\nServer Response - {response.text}")
        return 0


async def save_channel_access(user_id, channel_id):
    api_url = f"{API_URL}/ChannelAccess"

    data = {
        "userId": user_id,
        "channelId": int(channel_id) if channel_id is not None else None
    }

    response = requests.post(api_url, json=data, verify=Verify_value, headers=default_headers)
    if response.status_code == 201:
        return True
    else:
        logger.critical(
            f"Failed to save access info\nuser_id - {user_id}\nchannel_id - {channel_id}\nServer Response - {response.text}")
        return False


# Function to retrieve user's channels from the API
def get_user_channels(user_id: int) -> List[dict]:
    api_url = f"{API_URL}/Channel/ByUser/{user_id}"
    response = requests.get(api_url, verify=Verify_value, headers=default_headers)
    if response.status_code == 200:
        return response.json()
    else:
        return []


# Retrieve the current notification status from the API
def get_notification_status(channel_id):
    api_url = f"{API_URL}/Channel/{channel_id}"
    response = requests.get(api_url, verify=Verify_value, headers=default_headers)
    if response.status_code == 404:
        return None  # Channel not found

    channel_data = response.json()
    notifications_enabled = channel_data.get("notifications")

    if notifications_enabled is None:
        notifications_enabled = False  # Assume notifications are disabled if the value is null

    return notifications_enabled


# Toggle the notification status in the API
def toggle_notification_status(channel_id, new_notifications_enabled):
    api_toggle_url = f"{API_URL}/Channel/ToggleNotifications/{channel_id}"
    put_data = {"notifications": new_notifications_enabled}
    response = requests.put(api_toggle_url, json=put_data, verify=Verify_value, headers=default_headers)
    print(response.status_code)
    print(response.text)
    return response.status_code == 204


# Process channel bump
async def bump_channel(channel_id: int):
    api_url = f"{API_URL}/Channel/Bump/{channel_id}"

    try:
        response = requests.post(api_url, verify=Verify_value, headers=default_headers)
        return response
    except requests.exceptions.RequestException as e:
        # Handle exception (e.g., connection error)
        print("Error:", e)
        return None


# Function to retrieve the user ID from the database
async def get_user_id_from_database(user_id: int):
    try:
        # Make a GET request to the API endpoint for retrieving user by Telegram ID
        response = requests.get(f"{API_URL}/User/ByTelegramId/{user_id}", verify=Verify_value, headers=default_headers)
        if response.status_code == 200:
            user_data = response.json()
            if user_data:
                return user_data["id"]
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
        response = requests.get(f"{API_URL}/Channel/ByTelegramId/{channel_id}", verify=Verify_value, headers=default_headers)
        if response.status_code == 200:
            channel_data = response.json()
            if channel_data:
                return channel_data["id"]
            else:
                return None
        else:
            logger.critical(f"Error retrieving channel ID from the database. Status code: {response}")
            return None
    except Exception as e:
        print(f"Error retrieving channel ID from the database: {e}")
        return None


def get_notifications():
    url = f"{API_URL}/Notifications"

    try:
        response = requests.get(url, verify=Verify_value, headers=default_headers)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        notifications = response.json()
        return notifications
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving notifications: {e}")
        return []


async def get_tags():
    response = requests.get(f"{API_URL}/Tags", verify=Verify_value, headers=default_headers)
    if response.status_code == 200:
        tags_str = response.text.strip()
        tags = {tag: False for tag in tags_str.split(",")}
    else:
        tags = {}
    return tags


async def get_channel_tags(channel_id: int):
    # Get all tags from the API
    response = requests.get(f"{API_URL}/Tags", verify=Verify_value, headers=default_headers)
    if response.status_code == 200:
        tags_str = response.text.strip()
        tags = {tag: False for tag in tags_str.split(",")}
    else:
        tags = {}

    # Get the channel's tags from the API
    response = requests.get(f"{API_URL}/Channel/{channel_id}/Tags", verify=Verify_value, headers=default_headers)
    if response.status_code == 200:
        channel_tags = response.json()
        for tag in channel_tags:
            if tag in tags:
                tags[tag] = True

    return tags


def save_tags(channel_id: int, tags: dict):
    # Convert tags to a list of selected tags
    selected_tags = [tag for tag, selected in tags.items() if selected]

    # Make a PUT request to the API
    api_url = f"{API_URL}/Channel/{channel_id}/Tags"
    headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}  # Set the Content-Type header
    payload = json.dumps(selected_tags)  # Convert selected_tags to JSON
    response = requests.put(api_url, data=payload, headers=headers, verify=False)
    # Check the response status code
    if response.status_code == 204:
        print("Tags successfully sent to the API")
    else:
        print("Failed to send tags to the API")


def get_subscriptions_from_api():
    response = requests.get(f'{API_URL}/Subscription', verify=Verify_value, headers=default_headers)
    if response.status_code == 200:
        return response.json()
    else:
        # Handle error if API request fails
        logger.critical(f"Failed to get subscription types\n Server response - {response.text}")
        return None

def get_channel_tag_limit(channel_id):
    channel = getChannelById(channel_id)
    if channel is None:
        logger.error(f"Failed to get channel details for ID: {channel_id}")
        return None

    subType_id = channel.get('subType')
    if subType_id is None:
        logger.error(f"No subType found for channel ID: {channel_id}")
        return 3

    # Check for the special case where subType is 0
    if subType_id == 0:
        return 3

    subscriptions = get_subscriptions_from_api()
    if subscriptions is None:
        logger.error("Failed to get subscriptions")
        return 3

    for subType in subscriptions:
        if subType.get('id') == subType_id:
            return subType.get('tagLimit')

    logger.error(f"No matching subscription type found for channel ID: {channel_id}")
    return None

def subscribe_channel(channel_id, subtype_id):
    try:
        url = f"{API_URL}/Channel/Subscribe/{channel_id}?subtypeId={subtype_id}"
        response = requests.post(url, verify=Verify_value, headers=default_headers)

        if response.status_code == 200:
            return True, "Successfully subscribed the channel!"
        else:
            logger.critical(f"Failed to subscribe the channel.\n Server response - {response}")
            return False, "Failed to subscribe the channel. Please try again later."
    except requests.exceptions.RequestException:
        logger.critical(f"Failed to connect to the subscription service.\nServer response - {response}")
        return False, "Failed to connect to the subscription service. Please try again later."


# Retrieve the current promo post status from the API
def get_promo_post_status(channel_id):
    api_url = f"{API_URL}/Channel/{channel_id}"
    response = requests.get(api_url, verify=Verify_value, headers=default_headers)
    if response.status_code == 404:
        return None  # Channel not found

    channel_data = response.json()
    promo_post_enabled = channel_data.get("promoPost")

    if promo_post_enabled is None:
        promo_post_enabled = False  # Assume promo post is disabled if the value is null

    return promo_post_enabled


# Update the promo post status in the API
def toggle_promo_post_status(channel_id, new_promo_post_enabled):
    api_url = f"{API_URL}/Channel/TogglePromoPost/{channel_id}"
    put_data = {"notifications": new_promo_post_enabled}
    response = requests.put(api_url, put_data, verify=Verify_value, headers=default_headers)
    return response.status_code == 204  # Return True if the API update was successful


def update_channel_flag(channel_id, new_flag):
    """Update the flag of a given channel."""

    # Construct the endpoint URL
    endpoint = f"{API_URL}/Channel/{channel_id}/flag"

    # Make the PUT request to update the flag
    response = requests.put(endpoint, json={"flag": new_flag}, verify=Verify_value, headers=default_headers)

    # Check the response and handle errors
    if response.status_code == 204:
        print("Successfully updated the flag!")
    elif response.status_code == 404:
        print("Channel not found.")
    else:
        print("Failed to update the flag. Server responded with:", response.status_code, response.text)


async def update_channel_language(channel_id, new_language):
    """Update the language of a given channel."""

    # Construct the endpoint URL
    endpoint = f"{API_URL}/Channel/{channel_id}/language"
    # Prepare the payload
    payload = {"language": new_language}

    async with aiohttp.ClientSession() as session:
        async with session.put(endpoint, json=payload, headers=default_headers) as response:
            if response.status == 204:
                print("Successfully updated the language!")
            elif response.status == 404:
                print(f"Channel {channel_id} not found.")
            else:
                text = await response.text()
                print("Failed to update the language. Server responded with:", response.status, text)


async def is_user_admin(telegram_id):
    api_url = f'{API_URL}/Auth/IsAdmin/{telegram_id}'
    async with aiohttp.ClientSession(headers=default_headers) as session:
        async with session.get(api_url, ssl=False) as response:
            if response.status == 200:
                return await response.json()  # Assuming the API returns a JSON boolean
            else:
                return False  # Consider appropriate error handling


def updateChannelDetails(channel_id, promo_post_time, promo_post_interval):
    try:
        payload = {
            'PromoPostTime': promo_post_time,
            'PromoPostInterval': promo_post_interval
        }

        response = requests.put(
            f"{API_URL}/Channel/UpdatePromoPostDetails/{channel_id}",
            json=payload, verify=Verify_value, headers=default_headers
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


def getChannelById(channel_id):
    try:
        response = requests.get(f"{API_URL}/Channel/{channel_id}", verify=Verify_value, headers=default_headers)
        print(response)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

# async def get_user_notifications(telegram_id):
#     """
#     Function to get the notification settings for a specific user by their Telegram ID.
#
#     :param telegram_id: The Telegram ID of the user.
#     :return: A dictionary with notification types and their enabled/disabled status.
#     """
#     url = f"{API_URL}/Notification/{telegram_id}"
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url,  headers=default_headers) as response:
#             if response.status == 200:
#                 return await response.json()
#             else:
#                 return None  # or handle the error as appropriate
#
# async def updateChannelNotifications(telegram_id, notification_settings):
#     """
#     Function to update the notification settings for a specific user by their Telegram ID.
#
#     :param telegram_id: The Telegram ID of the user.
#     :param notification_settings: A dictionary with the new notification settings.
#     :return: True if the update was successful, False otherwise.
#     """
#     url = f"{API_URL}/Notification/SetNotificationSettings/{telegram_id}"
#     async with aiohttp.ClientSession() as session:
#         async with session.post(url, json=notification_settings,  headers=default_headers) as response:
#             return response.status == 200
