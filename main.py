from Handlers.channel_menu_handlers import *
from Handlers.menu_handlers import *
from Handlers.add_channel_handlers import *


if __name__ == "__main__":
    # Start the bot
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
