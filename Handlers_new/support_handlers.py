from aiogram import types
from aiogram.dispatcher.filters import Command
import aiohttp
import datetime

from api import API_URL, is_user_admin, is_user_support, hide_channel, send_to_admins
from bot import dp


@dp.message_handler(Command('support'))
async def open_support(message: types.Message):
    if not await is_user_support(message.from_user.id) and not await is_user_admin(message.from_user.id):
        await message.answer('У вас нет доступа к этой команде!')
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reports🚨', callback_data='support:reports'))

    await message.answer('Support menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'support')
async def open_support(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reports🚨', callback_data='support:reports'))

    await callback.message.edit_text('Support menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == 'support:reports')
async def support_channels(callback: types.CallbackQuery):
    await callback.answer()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Report/ActiveReports/{callback.from_user.id}', ssl=False) as response:
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


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:channel_select'))
async def support_channel_reports(callback: types.CallbackQuery):
    await callback.answer()
    channel_id = int(callback.data.split(':')[3])
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Report/ActiveReports/{callback.from_user.id}', ssl=False) as response:
            if response.status == 200:
                channels = await response.json()
            else:
                await callback.message.answer('Error while getting reports!')
                return

    selected_channel = None
    for channel in channels:
        if channel['channelId'] == channel_id:
            selected_channel = channel
            break
    reports = selected_channel['reports']

    keyboard = types.InlineKeyboardMarkup()
    for report in reports:
        date = datetime.datetime.strptime(report['reportTime'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%d.%m.%Y')
        callback_data = f'support:reports:report_select:{report["channelId"]}:{report["id"]}'
        keyboard.add(types.InlineKeyboardButton(f'{date}', callback_data=callback_data))
    keyboard.add(types.InlineKeyboardButton('Back', callback_data='support:reports'))

    await callback.message.edit_text(f'{selected_channel["channelName"]} Reports:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:report_select'))
async def support_channel_report(callback: types.CallbackQuery):
    await callback.answer()
    channel_id = int(callback.data.split(':')[3])
    report_id = int(callback.data.split(':')[4])
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Report/ActiveReports/{callback.from_user.id}', ssl=False) as response:
            if response.status == 200:
                channels = await response.json()
            else:
                await callback.message.answer('Error while getting reports!')
                return

    selected_channel = None
    selected_report = None
    for channel in channels:
        if channel['channelId'] == channel_id:
            selected_channel = channel
            for report in channel['reports']:
                if report['id'] == report_id:
                    selected_report = report
                    break
            break

    channel_link = selected_report['channelUrl']
    channel_name = selected_report['channelName']
    text = f"Id: {selected_report['id']}\n" \
        f'Channel: <a href="{channel_link}">{channel_name}</a>\n' \
        f"Date: {datetime.datetime.strptime(selected_report['reportTime'],'%Y-%m-%dT%H:%M:%S.%f').strftime('%d.%m.%Y')}\n" \
        f"Reason: {selected_report['reason']}\n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Channel page', url=selected_report['channelWebUrl']))
    keyboard.add(types.InlineKeyboardButton('Hide', callback_data=f'support:reports:hide:{selected_channel["channelId"]}:{selected_report["id"]}'))
    keyboard.add(types.InlineKeyboardButton('Send to Admins', callback_data=f'support:reports:send_to_admins:{selected_channel["channelId"]}:{selected_report["id"]}'))
    keyboard.add(types.InlineKeyboardButton('Back', callback_data=f'support:reports:channel_select:{selected_channel["channelId"]}'))

    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:hide'))
async def support_channel_report_hide(callback: types.CallbackQuery):
    await callback.answer()
    channel_id = int(callback.data.split(':')[3])
    report_id = int(callback.data.split(':')[4])

    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/Report/ActiveReports/{callback.from_user.id}', ssl=False) as response:
            if response.status == 200:
                channels = await response.json()
            else:
                await callback.message.answer('Error while getting reports!')
                return

    selected_channel = None
    selected_report = None
    for channel in channels:
        if channel['channelId'] == channel_id:
            selected_channel = channel
            for report in channel['reports']:
                if report['id'] == report_id:
                    selected_report = report
                    break
            break

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Yes', callback_data=f'support:reports:confirm_hide:{selected_channel["channelId"]}:{selected_report["id"]}'))
    keyboard.add(types.InlineKeyboardButton('Back', callback_data=f'support:reports:report_select:{selected_channel["channelId"]}:{selected_report["id"]}'))

    channel_name = selected_report['channelName']
    await callback.message.edit_text(f'Are you sure you want to hide {channel_name}?', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:confirm_hide'))
async def support_channel_report_hide_confirm(callback: types.CallbackQuery):
    channel_id = int(callback.data.split(':')[3])
    report_id = int(callback.data.split(':')[4])

    resp = await hide_channel(report_id, callback.from_user.id)

    await callback.answer('Channel hidden!', show_alert=True)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reports🚨', callback_data='support:reports'))

    await callback.message.edit_text('Support menu:', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:send_to_admins'))
async def support_channel_report_send_to_admins(callback: types.CallbackQuery):
    channel_id = int(callback.data.split(':')[3])
    report_id = int(callback.data.split(':')[4])

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Yes', callback_data=f'support:reports:confirm_send_to_admins:{channel_id}:{report_id}'))
    keyboard.add(types.InlineKeyboardButton('Back', callback_data=f'support:reports:report_select:{channel_id}:{report_id}'))

    await callback.message.edit_text(f'Are you sure you want to send report to admins?', reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith('support:reports:confirm_send_to_admins'))
async def support_channel_report_hide_confirm(callback: types.CallbackQuery):
    channel_id = int(callback.data.split(':')[3])
    report_id = int(callback.data.split(':')[4])

    await send_to_admins(callback.from_user.id, report_id)

    await callback.answer('Report was sent to Admins!', show_alert=True)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Reports🚨', callback_data='support:reports'))

    await callback.message.edit_text('Support menu:', reply_markup=keyboard)
