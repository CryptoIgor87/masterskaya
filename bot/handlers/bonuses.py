from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.callbacks.callback_data import SectionCallback, BonusCallback
from bot.keyboards.main_menu import bonus_keyboard, back_to_menu_keyboard
import database as db

router = Router()


@router.callback_query(SectionCallback.filter(F.name == "bonuses"))
async def show_bonuses(callback: CallbackQuery):
    await callback.answer()
    client = await db.get_client_by_telegram_id(callback.from_user.id)
    if not client:
        await callback.message.answer(
            "Произошла ошибка. Нажмите /start",
            reply_markup=back_to_menu_keyboard()
        )
        return

    total = await db.get_client_bonus_total(client["id"])
    unclaimed = await db.get_unclaimed_bonuses(client["id"])
    last_code = await db.get_last_claimed_code(client["id"])

    if total == 0 and not last_code:
        await callback.message.answer(
            "У вас пока нет доступных бонусов \U0001f614",
            reply_markup=back_to_menu_keyboard()
        )
        return

    if unclaimed:
        await callback.message.answer(
            f"\U0001f381 У вас <b>{total}</b> бонусов!\n\n"
            "Нажмите кнопку ниже, чтобы забрать их.",
            parse_mode="HTML",
            reply_markup=bonus_keyboard()
        )
    elif last_code:
        await callback.message.answer(
            f"\u2705 Ваши бонусы активны!\n\n"
            f"Ваш промокод: <b>{last_code}</b>",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard()
        )
    else:
        await callback.message.answer(
            "У вас пока нет доступных бонусов \U0001f614",
            reply_markup=back_to_menu_keyboard()
        )


@router.callback_query(BonusCallback.filter(F.action == "claim"))
async def claim_bonuses(callback: CallbackQuery):
    await callback.answer()
    client = await db.get_client_by_telegram_id(callback.from_user.id)
    if not client:
        return

    promo_code = await db.claim_bonuses(client["id"])

    if promo_code:
        await callback.message.answer(
            f"\U0001f389 Ваш промокод на бонусы: <b>{promo_code}</b>\n\n"
            "Покажите его при покупке!",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard()
        )
    else:
        last_code = await db.get_last_claimed_code(client["id"])
        if last_code:
            await callback.message.answer(
                f"\u2705 Ваши бонусы уже активны!\n\n"
                f"Ваш промокод: <b>{last_code}</b>",
                parse_mode="HTML",
                reply_markup=back_to_menu_keyboard()
            )
        else:
            await callback.message.answer(
                "У вас нет доступных бонусов для активации.",
                reply_markup=back_to_menu_keyboard()
            )
