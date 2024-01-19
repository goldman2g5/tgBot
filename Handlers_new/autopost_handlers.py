from aiogram import types

from bot import dp


@dp.callback_query_handler(lambda c: c.data == 'pass')
async def pass_(call: types.CallbackQuery):
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('autopost:instant:confirm'))
async def autopost_instant_confirm(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]

    await call.answer("Пост выложен!", show_alert=True)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Бамп", callback_data=f"bump_{channel_id}"),
        types.InlineKeyboardButton("Подписки", callback_data=f"subscription_{channel_id}_{channel_name}"),
        # TODO: notifications api
        types.InlineKeyboardButton("Уведомления", callback_data=f"notifications_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Автопост", callback_data=f"autopost_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Настройки", callback_data=f"customization_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Создать пост", callback_data=f"create_post_{channel_id}_{channel_name}"),
        types.InlineKeyboardButton("Назад", callback_data="manage_channels")
    )

    await call.message.edit_text(reply_markup=markup, text=f"@{channel_name} личный кабинет:")


@dp.callback_query_handler(lambda c: c.data.startswith('autopost:instant'))
async def autopost_instant(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]

    msg_text = "Подтвердите, что вы хотите выложить пост на своем канале с продвижением."

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Подтвердить",
                                            callback_data=f"autopost:instant:confirm_{channel_id}_{channel_name}"))
    keyboard.add(types.InlineKeyboardButton(text="Отмена", callback_data=f"autopost_{channel_id}_{channel_name}"))

    await call.message.edit_text(msg_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('autopost'))
async def autopost(call: types.CallbackQuery):
    channel_id = int(call.data.split("_")[1])
    channel_name = call.data.split("_")[2]

    msg_text = f"Настройка Автопоста для канала @{channel_name}\n" \
               "Автопост даёт дополнительные очки рейтинга раз в 1 день, а также возможность бампать у подписчиков канала\n" \
               "Пост выглядит так:\n\n" \
               "🔎 tgsearch.info (https://tgsearch.info/)\n\n" \
               "・Помоги любимому каналу в продвижении на лучшем телеграмм мониторинге! Нажми на кнопку как только она станет доступна!\n" \
               "・Последний кто вовремя нажал — @A1z7n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Бампнуть", callback_data=f"pass"))
    keyboard.add(types.InlineKeyboardButton(text=" ", callback_data=f"pass"))
    keyboard.add(
        types.InlineKeyboardButton(text="Моментальный", callback_data=f"autopost:instant_{channel_id}_{channel_name}"))
    keyboard.add(
        types.InlineKeyboardButton(text="По времени", callback_data=f"promotion_{channel_id}_{channel_name}"))
    keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data=f"channel_{channel_id}_{channel_name}"))

    await call.message.edit_text(msg_text, reply_markup=keyboard)
