import asyncio
import logging

from aiogram import Dispatcher

from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *
from Handlers.AdminPanelHandlers import *
from aiogram.utils import executor
from notification_service import start_notification_service
from bot import dp
from socket_service import *

from throthling_middleware import ThrottlingMiddleware


async def start_client():
    try:
        await client.start()
        me = await client.api.get_me()
        logging.info(f"Successfully logged in as {me.json()}")
    except Exception as e:
        logging.error(f"Error starting client: {e}")


async def on_startup_wrapper(dispatcher: Dispatcher):
    asyncio.create_task(connectToHub())
    asyncio.create_task(start_client())  # Starting the client as a background task
    await start_notification_service(dispatcher)


if __name__ == '__main__':
    # Set the log level for debugging
    logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w")

    # Initialize the event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Initialize the client (with your settings)

    # Setup middlewares
    # dp.middleware.setup(LoggingMiddleware())
    dp.middleware.setup(ThrottlingMiddleware())

    # Start the bot
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup_wrapper)
