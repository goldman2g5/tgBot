from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from api import *
from bot import dp, bot


@dp.callback_query_handler(lambda c: c.data == "back_to_admin_menu")
async def back_to_admin_menu_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.message.from_user.id

    # Define the markup based on admin status
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Reports", callback_data="reports")
    )

    if callback_query.message.reply_markup:
        # Edit the existing message with the updated inline keyboard
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=markup,
            text=f"Admin menu:",
        )
    else:
        # Send a new message with the inline keyboard
        await callback_query.message.answer(text="Main menu:", reply_markup=markup)


@dp.message_handler(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id

    # Check if the user is an admin
    isAdmin = await is_user_admin(user_id)

    # Define the markup based on admin status
    if isAdmin:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Reports", callback_data="reports")
        )
    else:
        return

    # Send the menu to the user
    await bot.send_message(message.chat.id, "Admin Menu:", reply_markup=markup)


@dp.message_handler(Command("reports"))
async def cmd_reports(message: types.Message):
    user_id = message.from_user.id
    api_url = f'https://localhost:7256/api/Auth/Reports/{user_id}'

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, ssl=False) as response:
            if response.status == 200:
                report_groups = await response.json()
                markup = InlineKeyboardMarkup()

                for group in report_groups:
                    text = f"{group['channelName']} - {group['reportCount']} Reports"
                    callback_data = f'group_details_{group["channelId"]}'
                    markup.add(InlineKeyboardButton(text, callback_data=callback_data))
                markup.add(InlineKeyboardButton("Back to Menu", callback_data="back_to_menu"))
                await message.answer(
                    "Select a report group to view:",
                    reply_markup=markup
                )
            else:
                await message.answer("Could not fetch reports. Please try again later.")


@dp.callback_query_handler(lambda c: c.data == 'reports')
async def display_reports(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    api_url = f'https://localhost:7256/api/Auth/Reports/{user_id}'

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, ssl=False) as response:
            if response.status == 200:
                report_groups = await response.json()
                markup = InlineKeyboardMarkup()

                for group in report_groups:
                    text = f"{group['channelName']} - {group['reportCount']} Reports"
                    callback_data = f'group_details_{group["channelId"]}'
                    markup.add(InlineKeyboardButton(text, callback_data=callback_data))
                markup.add(InlineKeyboardButton("Back to Menu", callback_data="back_to_admin_menu"))
                await bot.edit_message_text(
                    "Select a report group to view:",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=markup
                )
            else:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "Could not fetch reports. Please try again later."
                )

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('group_details_'))
async def view_report_group(callback_query: types.CallbackQuery):
    channel_id = int(callback_query.data.split('_')[-1])
    user_id = callback_query.from_user.id
    api_url = f'{API_URL}/Auth/Reports/{user_id}'

    is_admin = await is_user_admin(user_id)

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, ssl=False) as response:
            if response.status == 200:
                report_groups = await response.json()
                selected_group = next((group for group in report_groups if group["channelId"] == channel_id), None)

                if selected_group:
                    markup = InlineKeyboardMarkup()
                    for report in selected_group["reports"]:
                        text = f"Report by {report['reporteeName']} - {report['reportTime']}"
                        callback_data = f'viewreport_{report["id"]}'
                        if is_admin:
                            callback_data += '_admin'
                        markup.add(InlineKeyboardButton(text, callback_data=callback_data))

                    markup.add(InlineKeyboardButton("Back to Reports", callback_data="reports"))

                    await bot.edit_message_text(
                        f"Reports for {selected_group['channelName']}:",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        reply_markup=markup
                    )
                else:
                    await bot.send_message(
                        callback_query.message.chat.id,
                        "Report group not found."
                    )
            else:
                await bot.send_message(
                    callback_query.message.chat.id,
                    "Could not fetch report details. Please try again later."
                )

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('viewreport_'))
async def view_report_details(callback_query: types.CallbackQuery):
    parts = callback_query.data.split('_')
    report_id = int(parts[1])  # Convert report_id to an integer
    is_admin_view = len(parts) > 2 and parts[2] == 'admin'  # Check if it's an admin view

    telegram_id = callback_query.from_user.id
    report_url = f'{API_URL}/Auth/Report/{report_id}/{telegram_id}'

    async with aiohttp.ClientSession() as session:
        async with session.get(report_url, ssl=False) as response:
            if response.status == 200:
                report_data = await response.json()
                report_details = (f"Channel Name: {report_data['channelName']}\n"
                                  f"Channel URL: {report_data['channelWebUrl']}\n"
                                  f"Reportee Name: {report_data['reporteeName']}\n"
                                  f"Report Time: {report_data['reportTime']}\n"
                                  f"Text: {report_data['text']}\n"
                                  f"Reason: {report_data['reason']}\n"
                                  f"Status: {report_data['status']}\n")

                markup = types.InlineKeyboardMarkup()
                if is_admin_view:
                    markup.add(types.InlineKeyboardButton("Delete", callback_data=f"delete_{report_id}"))
                    markup.add(types.InlineKeyboardButton("Postpone", callback_data=f"postpone_{report_id}"))
                    markup.add(types.InlineKeyboardButton("Close", callback_data=f"close_{report_id}"))
                    markup.add(types.InlineKeyboardButton("Contact Owner", callback_data=f"contact_{report_id}"))
                else:
                    markup.add(
                        types.InlineKeyboardButton("Hide",
                                                   callback_data=view_report_cb.new(action="hide", id=report_id)))
                    markup.add(
                        types.InlineKeyboardButton("Skip",
                                                   callback_data=view_report_cb.new(action="skip", id=report_id)))

                report_msg = await bot.send_message(callback_query.from_user.id, report_details, reply_markup=markup)
            else:
                await bot.send_message(callback_query.from_user.id, "Could not retrieve the report details.")

    await callback_query.answer()


async def delete_bot_messages(chat_id, message_ids):
    for msg_id in message_ids:
        await bot.delete_message(chat_id, msg_id)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete_'))
async def handle_delete_request(callback_query: types.CallbackQuery):
    report_id = int(callback_query.data.split('_')[1])
    message_ids = []

    message_ids.append(callback_query.message.message_id)

    confirmation_msg = await bot.send_message(callback_query.from_user.id,
                                              "Are you sure you want to delete the channel? Type 'y' for Yes or 'n' for No.")
    message_ids.append(confirmation_msg.message_id)

    @dp.message_handler()
    async def handle_confirmation_response(message: types.Message):
        message_ids.append(message.message_id)
        if message.text.lower() == 'y':
            success_msg = await bot.send_message(message.from_user.id, "Channel deleted successfully.")
            message_ids.append(success_msg.message_id)
        elif message.text.lower() == 'n':
            cancel_msg = await bot.send_message(message.from_user.id, "Channel deletion cancelled.")
            message_ids.append(cancel_msg.message_id)
        else:
            invalid_msg = await bot.send_message(message.from_user.id, "Invalid response. Please type 'y' or 'n'.")
            message_ids.append(invalid_msg.message_id)

        await delete_bot_messages(callback_query.from_user.id, message_ids)

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('close_'))
async def handle_close_request(callback_query: types.CallbackQuery):
    report_id = int(callback_query.data.split('_')[1])
    message_ids = [callback_query.message.message_id]

    # Placeholder action for closing the report
    close_msg = await bot.send_message(callback_query.from_user.id, "Closing the report...")
    message_ids.append(close_msg.message_id)

    # Here, add your logic for closing the report

    # Send a final message and add its ID to the list
    final_msg = await bot.send_message(callback_query.from_user.id, "Report closed successfully.")
    message_ids.append(final_msg.message_id)

    # Delete all bot messages
    await delete_bot_messages(callback_query.from_user.id, message_ids)

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('postpone_'))
async def handle_postpone_request(callback_query: types.CallbackQuery):
    report_id = int(callback_query.data.split('_')[1])
    message_ids = [callback_query.message.message_id]

    # Placeholder action for postponing the report
    postpone_msg = await bot.send_message(callback_query.from_user.id, "Postponing the report...")
    message_ids.append(postpone_msg.message_id)

    # Here, add your logic for postponing the report

    # Send a final message and add its ID to the list
    final_msg = await bot.send_message(callback_query.from_user.id, "Report postponed successfully.")
    message_ids.append(final_msg.message_id)

    # Delete all bot messages
    await delete_bot_messages(callback_query.from_user.id, message_ids)

    await callback_query.answer()


# You will also need to handle the callback query when a button is pressed
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('report_details_'))
async def handle_report_details(callback_query: types.CallbackQuery):
    channel_id = callback_query.data.split('_')[-1]  # Extracting the channel ID from the callback data
    # You can now fetch the report details using the channel ID and display them or handle them as needed
    await callback_query.answer()  # Don't forget to answer the callback query
    # Add further implementation for showing report details as per your requirements


@dp.callback_query_handler(lambda c: c.data == 'remove_authorize_msg')
async def remove_authorization_messages(callback_query: types.CallbackQuery):
    # Deleting the success message
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


view_report_cb = CallbackData('report', 'action', 'id')


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('viewreport_'))
async def handle_view_report(callback_query: types.CallbackQuery):
    # Extract the report ID from the callback query data
    _, report_id = callback_query.data.split('_')
    report_id = int(report_id)  # Convert report_id to an integer if needed

    telegram_id = callback_query.from_user.id

    async with aiohttp.ClientSession() as session:
        # Adjust your API endpoint to include the Telegram ID
        report_url = f'{API_URL}/Auth/Report/{report_id}/{telegram_id}'
        print(report_url)

        # Make a GET request to your API endpoint
        async with session.get(report_url, ssl=False) as response:
            if response.status == 200:

                report_data = await response.json()  # Get the report data as JSON
                # Format a message to send to the user
                report_details = (f"Channel Name: {report_data['channelName']}\n"
                                  f"Channel URL: {report_data['channelWebUrl']}\n"
                                  f"Reportee Name: {report_data['reporteeName']}\n"
                                  f"Report Time: {report_data['reportTime']}\n"
                                  f"Text: {report_data['text']}\n"
                                  f"Reason: {report_data['reason']}\n")
                # Prepare the inline keyboard markup
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("Hide", callback_data=view_report_cb.new(action="hide", id=report_id)))
                markup.add(
                    types.InlineKeyboardButton("Skip", callback_data=view_report_cb.new(action="skip", id=report_id)))

                # Send the report details to the user with inline buttons
                await bot.send_message(callback_query.from_user.id, report_details, reply_markup=markup)
            else:
                # Send an error message if something goes wrong
                await bot.send_message(callback_query.from_user.id, "Could not retrieve the report details.")

                # Always answer the callback query
            await callback_query.answer()

    # Always answer the callback query, even if you do not send a message to the user
    await callback_query.answer()


@dp.callback_query_handler(view_report_cb.filter(action="hide"))
async def handle_hide(callback_query: types.CallbackQuery, callback_data: dict):
    report_id = int(callback_data['id'])
    telegram_id = callback_query.from_user.id
    status = 1  # "channel hidden"
    api_url = f'{API_URL}/Auth/CloseReport/{report_id}/{telegram_id}/{status}'

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, ssl=False) as response:
            if response.status == 200:
                await callback_query.answer("Report hidden and channel marked as hidden.", show_alert=True)
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
            else:
                await callback_query.answer("Failed to hide report.")


@dp.callback_query_handler(view_report_cb.filter(action="skip"))
async def handle_skip(callback_query: types.CallbackQuery, callback_data: dict):
    report_id = int(callback_data['id'])
    telegram_id = callback_query.from_user.id
    status = 0  # "closed"
    api_url = f'{API_URL}/Auth/CloseReport/{report_id}/{telegram_id}/{status}'

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, ssl=False) as response:
            if response.status == 200:
                await callback_query.answer("Report marked as closed.", show_alert=True)
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
            else:
                await callback_query.answer("Failed to close report.")


@dp.callback_query_handler(view_report_cb.filter(action="contact"))
async def handle_contact_owner(callback_query: types.CallbackQuery, callback_data: dict):
    # Implement contact owner logic
    await callback_query.answer("Contacting owner.")