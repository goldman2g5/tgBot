import asyncio
import logging
from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *
from Handlers.AdminPanelHandlers import *
from aiogram.utils import executor
from notification_service import start_notification_service
from bot import dp

from throthling_middleware import ThrottlingMiddleware




# Start the bot
if __name__ == '__main__':
    # Set the log level for debugging
    logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w")

    dp.middleware.setup(ThrottlingMiddleware())
    executor.start_polling(dp, skip_updates=True, on_startup=start_notification_service)
