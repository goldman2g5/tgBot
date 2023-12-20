from aiogram.dispatcher.filters.state import StatesGroup, State


# Class describing the states for adding a channel
class AddChannelStates(StatesGroup):
    sending_message = State()
    waiting_for_channel_name = State()
    waiting_for_check = State()
    waiting_for_channel_description = State()
    waiting_for_user_id = State()
    waiting_for_language_selection = State()
    waiting_for_flag_selection = State()
    waiting_for_description = State()
