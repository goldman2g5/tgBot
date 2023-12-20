import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiotdlib import Client
from pydantic import SecretStr
from pyrogram import Client as pClient

# Set the log level for debugging
logging.basicConfig(level=logging.INFO)

API_ID = 23558497
API_HASH = "2b461873dd2dea7e091f7af28fbe11e1"
api_hash_secret = SecretStr('API_HASH')
bot_token = '6488513477:AAHYdfO0qq_JhbsjVEYFyPpbtxUaxMkWomc'
bot_token_secret = SecretStr('6488513477:AAHYdfO0qq_JhbsjVEYFyPpbtxUaxMkWomc')
PHONE_NUMBER = "+79168355570"

client = Client(
     api_id=API_ID,
     api_hash=api_hash_secret,
     phone_number=PHONE_NUMBER,
     library_path='D:\\Program Files (D)\\td\\tdlib\\bin\\tdjson.dll'
)

pyro_client = pClient(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH,
)

# Initialize the bot and dispatcher
bot = Bot(token="6488513477:AAHYdfO0qq_JhbsjVEYFyPpbtxUaxMkWomc")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
