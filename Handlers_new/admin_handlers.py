import random

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
import aiohttp
from aiogram.dispatcher.filters.state import StatesGroup, State

from api import API_URL, is_user_admin, get_all_supports, remove_support, add_support
from bot import dp, bot


@dp.message_handler(Command('admin'))
async def open_admin(message: types.Message):
    if not await is_user_admin(message.from_user.id):
        await message.answer('У вас нет доступа к этой команде!')
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Скрытые', callback_data='admin:hidden'))
    keyboard.add(types.InlineKeyboardButton(text='Неразобранные', callback_data='admin:unresolved'))
    keyboard.add(types.InlineKeyboardButton(text='Саппорты', callback_data='admin:supports'))
    keyboard.add(types.InlineKeyboardButton(text='Репорты', callback_data='admin:reports'))

    await message.answer('Admin menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin')
async def open_admin(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Скрытые', callback_data='admin:hidden'))
    keyboard.add(types.InlineKeyboardButton(text='Неразобранные', callback_data='admin:unresolved'))
    keyboard.add(types.InlineKeyboardButton(text='Саппорты', callback_data='admin:supports'))
    keyboard.add(types.InlineKeyboardButton(text='Репорты', callback_data='admin:reports'))

    await callback.message.edit_text('Admin menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin:hidden')
async def admin_hidden(callback: types.CallbackQuery):
    await callback.answer()

    # need api call


@dp.callback_query_handler(lambda call: call.data == 'admin:unresolved')
async def admin_unresolved(callback: types.CallbackQuery):
    await callback.answer()

    # need api call


@dp.callback_query_handler(lambda call: call.data == 'admin:supports', state='*')
async def admin_supports(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Список саппортов', callback_data='admin:supports:list'))
    keyboard.add(types.InlineKeyboardButton(text='Добавить саппорта', callback_data='admin:supports:add'))
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='admin'))

    await callback.message.edit_text('Меню саппортов:', reply_markup=keyboard)


class AddSupportStates(StatesGroup):
    username = State()


@dp.callback_query_handler(lambda call: call.data == 'admin:supports:add')
async def add_support_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='admin:supports'))

    await AddSupportStates.username.set()
    async with state.proxy() as data:
        data['messages_to_delete'] = [callback.message.message_id]
    await callback.message.edit_text('Чтобы добавить саппорта напишите тег', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'add_support_cancel')
async def cancel(callback: types.CallbackQuery):
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Список саппортов', callback_data='admin:supports:list'))
    keyboard.add(types.InlineKeyboardButton(text='Добавить саппорта', callback_data='admin:supports:add'))
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='admin'))

    await callback.message.edit_text('Меню саппортов:', reply_markup=keyboard)

@dp.message_handler(state=AddSupportStates.username)
async def confirm_add_support(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        messages_to_delete = data['messages_to_delete']

    for message_id in messages_to_delete:
        await bot.delete_message(message.from_user.id, message_id)

    await state.finish()

    support = message.text
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Подтверждаю', callback_data=f'add_support_confirm:{support}'))
    keyboard.add(types.InlineKeyboardButton('Отмена', callback_data='add_support_cancel'))

    await message.answer(f'Вы точно хотите дать права саппорта - {support}?', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('add_support_confirm:'))
async def support_added(callback: types.CallbackQuery):
    support = callback.data.split(':')[1]

    await add_support(callback.from_user.id, support)

    await callback.message.edit_text(f'{support} успешно добавлен в список саппортов')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Скрытые', callback_data='admin:hidden'))
    keyboard.add(types.InlineKeyboardButton(text='Неразобранные', callback_data='admin:unresolved'))
    keyboard.add(types.InlineKeyboardButton(text='Саппорты', callback_data='admin:supports'))
    keyboard.add(types.InlineKeyboardButton(text='Репорты', callback_data='admin:reports'))

    await callback.message.answer('Admin menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin:supports:list')
async def admin_supports_list(callback: types.CallbackQuery):
    await callback.answer()

    supports = await get_all_supports(callback.from_user.id)

    keyboard = types.InlineKeyboardMarkup()
    for support in supports:
        keyboard.add(types.InlineKeyboardButton(text=support['telegramId'],
                                                callback_data=f'admin:supports:select:{support["telegramId"]}'))

    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='admin:supports'))

    await callback.message.edit_text('Список саппортов:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('admin:supports:select:'))
async def select_support(callback: types.CallbackQuery):
    await callback.answer()

    support_id = callback.data.split(':')[3]

    resolved_reports = random.randint(0, 100)  # TODO: API
    unresolved_reports = random.randint(0, 100)
    hidden_channels = random.randint(0, 100)

    text = f'<b>Саппорт:</b> <code>{support_id}</code>\n\n' \
           f'<b>Разобрано репортов:</b> <code>{resolved_reports}</code>\n' \
           f'<b>Неразобраных репортов:</b> <code>{unresolved_reports}</code>\n' \
           f'<b>Скрытых каналов:</b> <code>{hidden_channels}</code>\n'

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Удалить саппорта', callback_data=f'admin:support:remove:{support_id}'))
    keyboard.add(types.InlineKeyboardButton('Назад', callback_data='admin:supports:list'))

    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('admin:support:remove:'))
async def admin_remove_support(callback: types.CallbackQuery):
    await callback.answer()

    support_id = callback.data.split(':')[3]

    text = f'<b>Вы точно хотите удалить саппорта:</b> <code>{support_id}</code>'

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Подтверждаю', callback_data=f'admin:support:confirm_remove:{support_id}'))
    keyboard.add(types.InlineKeyboardButton('Отмена', callback_data=f'admin:supports:select:{support_id}'))

    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('admin:support:confirm_remove:'))
async def confirm_remove(callback: types.CallbackQuery):
    support_id = callback.data.split(':')[3]

    if await remove_support(callback.from_user.id, support_id):
        await callback.answer('Успешно.', show_alert=True)
    else:
        await callback.answer('Ошибка при удалении саппорта', show_alert=True)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Скрытые', callback_data='admin:hidden'))
    keyboard.add(types.InlineKeyboardButton(text='Неразобранные', callback_data='admin:unresolved'))
    keyboard.add(types.InlineKeyboardButton(text='Саппорты', callback_data='admin:supports'))
    keyboard.add(types.InlineKeyboardButton(text='Репорты', callback_data='admin:reports'))

    await callback.message.edit_text('Admin menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin:reports')
async def admin_reports(callback: types.CallbackQuery):
    await callback.answer()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Admin/Reports/{callback.from_user.id}', ssl=False) as response:
            if response.status == 200:
                channels = await response.json()
            else:
                await callback.message.answer('Error while getting reports!')
                return

    keyboard = types.InlineKeyboardMarkup()
    for channel in channels:
        text = f"{channel['channelName']} - {channel['reportCount']} Reports"
        callback_data = f'support:reports:channel_select:{channel["channelId"]}'
        keyboard.add(types.InlineKeyboardButton(text, callback_data=callback_data))
    keyboard.add(types.InlineKeyboardButton('Back', callback_data='support'))

    await callback.message.edit_text('Channels:', reply_markup=keyboard)
