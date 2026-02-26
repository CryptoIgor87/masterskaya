from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.main_menu import main_menu_keyboard
from bot.callbacks.callback_data import NavigationCallback
import database as db

router = Router()

DEFAULT_WELCOME = "Добро пожаловать в наш магазин! \U0001f44b"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    await state.clear()

    # Handle giveaway deep links
    if command.args and command.args.startswith("gw_"):
        from bot.handlers.giveaways import handle_giveaway_entry
        await handle_giveaway_entry(message, command.args)
        return

    welcome = await db.get_setting("welcome_text") or DEFAULT_WELCOME
    await message.answer(
        f"{welcome}\n\nЗаберите ваши бонусы нажав кнопку ниже \u2b07\ufe0f",
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
