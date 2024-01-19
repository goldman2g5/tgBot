import asyncio
import logging

from aiogram import Dispatcher

from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *

from Handlers_new.notifications_settings import *
from Handlers_new.admin_handlers import *
from Handlers_new.support_handlers import *
from Handlers_new.autopost_handlers import *


from aiogram.utils import executor
from notification_service import start_notification_service
from bot import dp, pyro_client
from socket_service import *

from throthling_middleware import ThrottlingMiddleware


async def start_pyro_client():
    print("Starting pyro client")
    await pyro_client.start()


async def on_startup_wrapper(dispatcher: Dispatcher):
    # await start_client()
    await asyncio.gather(
        start_pyro_client(),
        connectToHub(),
        start_notification_service(dispatcher),
        dispatcher.start_polling()
    )


if __name__ == '__main__':
    # Set the log level for debugging
    logging.basicConfig(level=logging.INFO)

    # Setup middlewares
    # dp.middleware.setup(LoggingMiddleware())
    dp.middleware.setup(ThrottlingMiddleware())

    # Start the bot
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup_wrapper)
