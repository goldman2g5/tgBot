import configparser
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiotdlib import Client
from pydantic import SecretStr
from pyrogram import Client as pyroClient
from aiotdlib.api import UpdateAuthorizationState, AuthorizationStateWaitPhoneNumber, AuthorizationStateWaitCode

# Set the log level for debugging
logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')

API_ID = config['bot']['API_ID']
API_HASH = config['bot']['API_HASH']
api_hash_secret = SecretStr(config['bot']['API_HASH'])
bot_token = config['bot']['BOT_TOKEN']
bot_token_secret = SecretStr(config['bot']['BOT_TOKEN'])
PHONE_NUMBER = config['bot']['PHONE_NUMBER']

pyro_client = pyroClient(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH
)

# Initialize the bot and dispatcher
bot = Bot(token=config['bot']['BOT_TOKEN'])
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
