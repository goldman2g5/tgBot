from aiogram import types

from bot import dp


@dp.message_handler(commands=['help'])
async def help_cmd(message: types.Message):
    text = ("pampam")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Написать в поддержку", url="t.me/durov"))
    keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data="back_to_menu"))

    await message.answer(text, reply_markup=keyboard)
