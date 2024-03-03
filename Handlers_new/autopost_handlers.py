from aiogram import types
from aiogram.types import InputFile, InputMediaPhoto

from api import get_channel_url_by_id, get_channel_id_by_id
from bot import dp, bot


@dp.callback_query_handler(lambda c: c.data == 'pass')
async def pass_(call: types.CallbackQuery):
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('autopost:instant:confirm'))
async def autopost_instant_confirm(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]
    channel_link = await get_channel_url_by_id(channel_id)
    channel_telegram_id = await get_channel_id_by_id(channel_id)

    text = '🔎 <a href="https://tgsearch.info/">tgsearch.info</a>\n\n' \
           "<b>・Помоги любимому каналу в продвижении на лучшем телеграмм мониторинге! Нажми на кнопку как только она станет доступна!</b>\n" \
           "<b>・Будь первым кто бампнет канал!</b>"

    bump_keyboard = types.InlineKeyboardMarkup()
    bump_keyboard.add(types.InlineKeyboardButton('Бамп', callback_data=f'bump_{channel_id}'))

    await bot.send_message(channel_telegram_id, text, reply_markup=bump_keyboard)

    await call.answer("Пост выложен!", show_alert=True)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Бамп", callback_data=f"bump_{channel_id}"),
        types.InlineKeyboardButton("Подписки", callback_data=f"subscription_{channel_id}_{channel_name}"),
        # types.InlineKeyboardButton("Уведомления", callback_data=f"notifications_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Рекламный пост", callback_data=f"autopost_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Настройки", callback_data=f"customization_{channel_id}_{channel_name}"),
        # types.InlineKeyboardButton("Создать пост", callback_data=f"create_post_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Назад", callback_data="manage_channels")
    )

    await call.message.delete()
    await call.message.answer(reply_markup=markup, text=f"{channel_link} личный кабинет:")


@dp.callback_query_handler(lambda c: c.data.startswith('autopost:instant'))
async def autopost_instant(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]
    channel_link = await get_channel_url_by_id(channel_id)

    msg_text = f"Подтвердите, что вы хотите выложить пост на своем канале {channel_link}"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Подтвердить",
                                            callback_data=f"autopost:instant:confirm_{channel_id}_{channel_name}"))
    keyboard.add(types.InlineKeyboardButton(text="Отмена", callback_data=f"autopost_{channel_id}_{channel_name}"))

    await call.message.delete()
    await call.message.answer(msg_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('autopost'))
async def autopost(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]

    file = InputFile('example_post.png')
    msg_text = "<b>Пост выглядит так ☝️</b>\n"\
               "Рекламный пост даёт дополнительные очки рейтинга 1 раз в день, а также возможность бампать подписчикам канала.\n"

    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Выложить пост",
                                            callback_data=f"autopost:instant_{channel_id}_{channel_name}"))
    keyboard.add(types.InlineKeyboardButton(text="Отмена", callback_data=f"channel_{channel_id}_{channel_name}_respawn"))

    await call.message.delete()
    await call.message.answer_photo(file, caption=msg_text, reply_markup=keyboard)

    # keyboard = types.InlineKeyboardMarkup()
    # keyboard.add(
    #     types.InlineKeyboardButton(text="Моментальный", callback_data=f"autopost:instant_{channel_id}_{channel_name}"))
    # keyboard.add(
    #     types.InlineKeyboardButton(text="По времени", callback_data=f"promotion_{channel_id}_{channel_name}_respawn"))
    # keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data=f"channel_{channel_id}_{channel_name}_respawn"))
    #
    # file = InputFile('example_post.png')
    # await call.message.delete()
    # await call.message.answer_photo(file, caption=msg_text, reply_markup=keyboard)
    # await call.message.edit_text(msg_text, reply_markup=keyboard)
