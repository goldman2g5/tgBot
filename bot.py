import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiotdlib import Client
from pydantic import SecretStr
from aiotdlib.api import UpdateAuthorizationState, AuthorizationStateWaitPhoneNumber, AuthorizationStateWaitCode

# Set the log level for debugging
logging.basicConfig(level=logging.INFO)

API_ID = 23558497
API_HASH = "2b461873dd2dea7e091f7af28fbe11e1"
api_hash_secret = SecretStr('API_HASH')
bot_token = '6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4'
bot_token_secret = SecretStr('6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4')
PHONE_NUMBER = "+79103212166"

client = Client(
     api_id=API_ID,
     api_hash=API_HASH,
     phone_number=PHONE_NUMBER,
     library_path='C:/Users/Timar/td/tdlib/bin/tdjson.dll'
)

# Initialize the bot and dispatcher
bot = Bot(token="6415611500:AAEZCM43HfrQl0PbExLcoIK33Eze8remjlQ")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
