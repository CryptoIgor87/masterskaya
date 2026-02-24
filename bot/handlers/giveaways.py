import random

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.callbacks.callback_data import GiveawayCaptchaCallback
from bot.keyboards.main_menu import back_to_menu_keyboard
import database as db

router = Router()

# Store correct answers: {message_id: correct_answer}
_captcha_answers: dict[int, int] = {}


def _make_captcha_keyboard(giveaway_id: int) -> tuple[str, InlineKeyboardMarkup, int]:
    """Generate a math captcha and return (question_text, keyboard, correct_answer)."""
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    correct = a + b

    # Generate 3 wrong answers (distinct from correct)
    wrong = set()
    while len(wrong) < 3:
        w = random.randint(max(2, correct - 10), correct + 10)
        if w != correct and w > 0:
            wrong.add(w)

    options = [correct] + list(wrong)
    random.shuffle(options)

    buttons = [
        InlineKeyboardButton(
            text=str(opt),
            callback_data=GiveawayCaptchaCallback(giveaway_id=giveaway_id, answer=opt).pack(),
        )
        for opt in options
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    question = f"\U0001f9e9 Сколько будет <b>{a} + {b}</b>?"
    return question, keyboard, correct


async def handle_giveaway_entry(message: Message, deep_link_code: str):
    """Called from start handler when deep link starts with gw_."""
    gw = await db.get_giveaway_by_code(deep_link_code)
    if not gw:
        await message.answer(
            "\u274c Розыгрыш не найден.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    if gw["status"] != "active":
        await message.answer(
            "\u23f0 Этот розыгрыш уже завершён.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    client = await db.get_client_by_telegram_id(message.from_user.id)
    if not client:
        await message.answer(
            "\u274c Произошла ошибка. Нажмите /start",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    # Check if already participating
    participants = await db.get_giveaway_participants(gw["id"])
    already_in = any(p["telegram_id"] == message.from_user.id for p in participants)

    if already_in:
        await message.answer(
            f"\u2705 Вы уже участвуете в розыгрыше <b>«{gw['title']}»</b>!\n\n"
            "Ожидайте результатов \U0001f340",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    # Show captcha
    question, keyboard, correct = _make_captcha_keyboard(gw["id"])
    sent = await message.answer(
        f"\U0001f3b0 Розыгрыш: <b>«{gw['title']}»</b>\n\n"
        f"Для участия решите пример:\n{question}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    _captcha_answers[sent.message_id] = correct


@router.callback_query(GiveawayCaptchaCallback.filter())
async def captcha_answer(callback: CallbackQuery, callback_data: GiveawayCaptchaCallback):
    await callback.answer()

    msg_id = callback.message.message_id
    correct = _captcha_answers.get(msg_id)

    if correct is None:
        await callback.message.edit_text(
            "\u274c Капча устарела. Перейдите по ссылке розыгрыша ещё раз.",
        )
        return

    if callback_data.answer != correct:
        # Wrong answer — generate new captcha
        _captcha_answers.pop(msg_id, None)
        question, keyboard, new_correct = _make_captcha_keyboard(callback_data.giveaway_id)
        await callback.message.edit_text(
            f"\u274c Неверно! Попробуйте ещё раз:\n{question}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        _captcha_answers[msg_id] = new_correct
        return

    # Correct answer — register participant
    _captcha_answers.pop(msg_id, None)

    client = await db.get_client_by_telegram_id(callback.from_user.id)
    if not client:
        await callback.message.edit_text("\u274c Произошла ошибка. Нажмите /start")
        return

    gw = await db.get_giveaway(callback_data.giveaway_id)
    if not gw or gw["status"] != "active":
        await callback.message.edit_text("\u23f0 Этот розыгрыш уже завершён.")
        return

    added = await db.add_giveaway_participant(gw["id"], client["id"])
    if added:
        await callback.message.edit_text(
            f"\u2705 Вы участвуете в розыгрыше <b>«{gw['title']}»</b>!\n\n"
            "Ожидайте результатов \U0001f340",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"\u2705 Вы уже участвуете в розыгрыше <b>«{gw['title']}»</b>!\n\n"
            "Ожидайте результатов \U0001f340",
            parse_mode="HTML",
        )
