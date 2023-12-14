import asyncio
import logging
from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *
from Handlers.AdminPanelHandlers import *
from aiogram.utils import executor
from notification_service import start_notification_service
from bot import dp
from socket_service import *

from throthling_middleware import ThrottlingMiddleware




# Start the bot
if __name__ == '__main__':
    # Set the log level for debugging
    logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w")
    print(f"connectionId: {negotiation['connectionId']}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connectToHub(negotiation['connectionId']))
    dp.middleware.setup(ThrottlingMiddleware())
    executor.start_polling(dp, skip_updates=True, on_startup=start_notification_service)
