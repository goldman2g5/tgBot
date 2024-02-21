from aiogram import types
from aiogram.dispatcher import FSMContext

from api import get_user_notifications_settings, set_user_notifications_settings
from bot import dp


@dp.callback_query_handler(lambda c: c.data == "xxx_notifications_settings")
async def notifications_settings_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_settings = await get_user_notifications_settings(callback_query.from_user.id)
    translation = {'bump': "Бампы", 'important': "Важные"}

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for setting in user_settings:
        if user_settings[setting]:
            keyboard.add(types.InlineKeyboardButton(f"{translation[setting]}: ✅", callback_data=f"toggle_{setting}"))
        else:
            keyboard.add(types.InlineKeyboardButton(f"{translation[setting]}: ❌", callback_data=f"toggle_{setting}"))

    keyboard.add(types.InlineKeyboardButton("В главное меню", callback_data="back_to_menu"))

    await callback_query.message.edit_text("Настройки уведомлений:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("toggle_"))
async def toggle_notifications_setting_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    setting = callback_query.data.split("_")[1]

    user_settings = await get_user_notifications_settings(callback_query.from_user.id)
    user_settings[setting] = not user_settings[setting]
    settings_json = {"bump": user_settings["bump"], "important": user_settings["important"]}
    await set_user_notifications_settings(callback_query.from_user.id, settings_json)
    user_settings = await get_user_notifications_settings(callback_query.from_user.id)

    translation = {'bump': "Бампы", 'important': "Важные"}

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for setting in user_settings:
        if user_settings[setting]:
            keyboard.add(types.InlineKeyboardButton(f"{translation[setting]}: ✅", callback_data=f"toggle_{setting}"))
        else:
            keyboard.add(types.InlineKeyboardButton(f"{translation[setting]}: ❌", callback_data=f"toggle_{setting}"))

    keyboard.add(types.InlineKeyboardButton("В главное меню", callback_data="back_to_menu"))

    await callback_query.message.edit_text("Настройки уведомлений:", reply_markup=keyboard)
