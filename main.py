import asyncio
from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *
from aiogram.utils import executor
from notification_service import start_notification_service




# Start the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=start_notification_service)
