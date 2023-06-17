import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Set the log level for debugging
logging.basicConfig(level=logging.INFO)

# Initialize the bot and dispatcher
bot = Bot(token="6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)