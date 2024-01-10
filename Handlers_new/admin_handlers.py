from aiogram import types
from aiogram.dispatcher.filters import Command
import aiohttp
import datetime

from api import API_URL, is_user_admin, get_all_supports
from bot import dp, pyro_client


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


@dp.callback_query_handler(lambda call: call.data == 'admin:hidden')
async def admin_hidden(callback: types.CallbackQuery):
    await callback.answer()

    # need api call


@dp.callback_query_handler(lambda call: call.data == 'admin:unresolved')
async def admin_unresolved(callback: types.CallbackQuery):
    await callback.answer()

    # need api call


@dp.callback_query_handler(lambda call: call.data == 'admin:supports')
async def admin_supports(callback: types.CallbackQuery):
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Список саппортов', callback_data='admin:supports:list'))
    keyboard.add(types.InlineKeyboardButton(text='Добавить саппорта', callback_data='admin:supports:add'))

    await callback.message.edit_text('Меню саппортов:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin:supports:list')
async def admin_supports_list(callback: types.CallbackQuery):
    await callback.answer()

    supports = await get_all_supports(callback.from_user.id)

    keyboard = types.InlineKeyboardMarkup()
    for support in supports:
        keyboard.add(types.InlineKeyboardButton(text=support['telegramId'], callback_data=f'admin:supports:select:{support["telegramId"]}'))

    await callback.message.edit_text('Список саппортов:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'admin:reports')
async def admin_reports(callback: types.CallbackQuery):
    await callback.answer()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Auth/Reports/{callback.from_user.id}', ssl=False) as response:
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
