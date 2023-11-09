import aiohttp
from aiogram import types
from bot import dp, bot
from api import API_URL


# @dp.callback_query_handler(lambda c: c.data and c.data.startswith('viewreport_'))
# async def handle_view_report(callback_query: types.CallbackQuery):
#     print("хуй")
#     # Extract the report ID from the callback query data
#     _, report_id = callback_query.data.split('_')
#     report_id = int(report_id)  # Convert report_id to an integer if needed
#
#     async with aiohttp.ClientSession() as session:
#         # Assuming your API endpoint to get the report looks like this
#         report_url = f'{API_URL}/Report/{report_id}'
#
#         # Make a GET request to your API endpoint
#         async with session.get(report_url, ssl=False) as response:
#             print("жопа")
#             if response.status == 200:
#                 report_data = await response.json()  # Get the report data as JSON
#                 # Format a message to send to the user
#                 report_details = (f"Report ID: {report_data['Id']}\n"
#                                   f"Reportee: {report_data['ReporteeName']}\n"
#                                   f"Channel: {report_data['ChannelName']}\n"
#                                   f"Reason: {report_data['Reason']}\n"
#                                   f"Text: {report_data['Text']}")
#                 # Send the report details to the user
#                 await bot.send_message(callback_query.from_user.id, report_details)
#                 print("ебаааать")
#             else:
#                 # Send an error message if something goes wrong
#                 await bot.send_message(callback_query.from_user.id, "Could not retrieve the report details.")
#                 print("паравоз")
#
#     # Always answer the callback query, even if you do not send a message to the user
#     await callback_query.answer()
