from aiogram.fsm.state import State, StatesGroup

class GameStates(StatesGroup):
    IDLE = State()
    CHOOSING_GENDER = State()
    CHOOSING_DISTANCE = State()
    WAITING_JOIN = State()
    INTRO = State()
    ROUND_ACTIVE = State()
    WAITING_ANSWERS = State()
    GUESSING = State()
    RESULTS = State()
