from aiogram import Dispatcher

from aiogram.utils import executor
from notification_service import start_notification_service
from bot import dp
from socket_service import *
from bot import pyro_client

from throthling_middleware import ThrottlingMiddleware


async def start_client():
    print("Starting client...")
    try:
        await client.start()
        me = await client.api.get_me()
        logging.info(f"Successfully logged in as {me.json()}")
    except Exception as e:
        logging.error(f"Error starting client: {e}")


async def start_pyro_client():
    print("Starting pyro client")
    await pyro_client.start()


async def on_startup_wrapper(dispatcher: Dispatcher):
    await asyncio.gather(
        start_pyro_client(),
        connectToHub(),
        start_client(),
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
