from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.callbacks.callback_data import SectionCallback, FeedbackReplyCallback
from bot.keyboards.main_menu import back_to_menu_keyboard
from bot.states.feedback_states import FeedbackStates
from config import ADMIN_USER_ID
import database as db

router = Router()


@router.callback_query(SectionCallback.filter(F.name == "feedback"))
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(FeedbackStates.waiting_for_message)
    await callback.message.answer(
        "\u270f\ufe0f Напишите ваше сообщение, и мы ответим вам в ближайшее время.\n\n"
        "Для отмены нажмите /start"
    )


@router.message(FeedbackStates.waiting_for_message)
async def receive_feedback(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    client = await db.get_client_by_telegram_id(message.from_user.id)
    if not client:
        await message.answer("Произошла ошибка. Нажмите /start")
        return

    feedback_id = await db.save_feedback(client["id"], message.text)

    await message.answer(
        "\u2705 Ваше сообщение отправлено! Мы скоро ответим.",
        reply_markup=back_to_menu_keyboard()
    )

    # Send to admin
    name = message.from_user.full_name
    username = f" (@{message.from_user.username})" if message.from_user.username else ""

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="\u2709\ufe0f Ответить",
        callback_data=FeedbackReplyCallback(feedback_id=feedback_id).pack()
    ))

    await bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            f"\U0001f4e8 <b>Новое сообщение</b>\n\n"
            f"От: {name}{username}\n"
            f"Текст: {message.text}"
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(FeedbackReplyCallback.filter())
async def admin_reply_start(callback: CallbackQuery, callback_data: FeedbackReplyCallback, state: FSMContext):
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("Только для администратора", show_alert=True)
        return

    await callback.answer()
    await state.set_state(FeedbackStates.waiting_for_admin_reply)
    await state.update_data(feedback_id=callback_data.feedback_id)
    await callback.message.answer("\u270f\ufe0f Введите ответ клиенту:")


@router.message(FeedbackStates.waiting_for_admin_reply)
async def admin_reply_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    feedback_id = data.get("feedback_id")
    await state.clear()

    if not feedback_id:
        await message.answer("Ошибка: не найден ID сообщения.")
        return

    feedback = await db.get_feedback(feedback_id)
    if not feedback:
        await message.answer("Сообщение не найдено.")
        return

    await db.set_feedback_reply(feedback_id, message.text)

    client = await db.get_client(feedback["client_id"])
    if not client:
        await message.answer("Клиент не найден.")
        return

    await bot.send_message(
        chat_id=client["telegram_id"],
        text=f"\U0001f4ac <b>Ответ от магазина:</b>\n\n{message.text}",
        parse_mode="HTML"
    )

    await message.answer("\u2705 Ответ отправлен клиенту!")
