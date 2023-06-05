import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Устанавливаем уровень логов для отладки
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчера
bot = Bot(token="6073155840:AAEq_nWhpl5qHjIpEEHKQ0cq9GeF_l0cJo4")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Класс, описывающий состояния для добавления канала
class AddChannelStates(StatesGroup):
    waiting_for_channel_name = State()
    waiting_for_check = State()


# Функция для проверки добавления бота на канал
async def check_bot_in_channel(channel_name: str) -> bool:
    try:
        chat = await bot.get_chat(channel_name)
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status == "administrator":
            return True
    except Exception as e:
        logging.error(f"Error checking bot membership: {e}")
    return False


# Обработчик команды /start
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем кнопки для меню
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Добавить канал", callback_data="add_channel"),
               InlineKeyboardButton("Управление каналами", callback_data="manage_channels"))

    await message.answer("Меню:", reply_markup=markup)


# Обработчик нажатий на кнопки меню
@dp.callback_query_handler(lambda c: c.data in ["add_channel", "manage_channels"])
async def process_menu_callbacks(callback_query: types.CallbackQuery):
    if callback_query.data == "add_channel":
        await AddChannelStates.waiting_for_channel_name.set()
        await callback_query.message.answer("Для размещения канала на мониторинге, "
                                             "нужно добавить бота на канал. "
                                             "Пожалуйста, введите имя канала:")
    elif callback_query.data == "manage_channels":
        await callback_query.message.answer("Функционал управления каналами в разработке.")


# Обработчик ввода имени канала
@dp.message_handler(state=AddChannelStates.waiting_for_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    channel_name = "@" + message.text

    # Сохраняем имя канала в контексте
    await state.update_data(channel_name=channel_name)

    # Создаем кнопку "Добавить бота" и отправляем сообщение
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Проверить", callback_data="add_bot"))
    await message.answer("Для размещения канала на мониторинге, "
                         "нужно добавить бота на канал.", reply_markup=markup)

    await AddChannelStates.waiting_for_check.set()

# Обработчик нажатия на кнопку "Добавить бота"
@dp.callback_query_handler(state=AddChannelStates.waiting_for_check, text="add_bot")
async def process_add_bot(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_name = data.get("channel_name")

    user = callback_query.from_user

    # Проверяем добавление бота на канал
    if await check_bot_in_channel(channel_name):
        await state.finish()
        await callback_query.message.answer("Успешно! Бот добавлен на канал")
    else:
        await callback_query.message.answer("Ошибка: бот не был добавлен на канал.")

    # Проверяем, является ли пользователь администратором канала
    try:
        chat = await bot.get_chat(channel_name)
        member = await bot.get_chat_member(chat.id, user.id)
        if member.status in ("administrator", "creator"):
            await state.finish()
            await callback_query.message.answer("Успешно! Пользователь является администратором канала.")
        else:
            await callback_query.message.answer("Ошибка: вы не являетесь администратором указанного канала.")
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при проверке: {e}")




if __name__ == "__main__":
    # Запуск бота
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
