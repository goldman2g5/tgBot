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
