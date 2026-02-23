from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.main_menu import main_menu_keyboard
from bot.callbacks.callback_data import NavigationCallback

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Добро пожаловать в наш магазин! \U0001f44b\n\n"
        "Выберите интересующий раздел:",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(NavigationCallback.filter(F.action == "back_to_menu"))
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "Главное меню \U0001f3e0\n\nВыберите раздел:",
        reply_markup=main_menu_keyboard()
    )
