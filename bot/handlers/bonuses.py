from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.callbacks.callback_data import SectionCallback, BonusCallback
from bot.keyboards.main_menu import back_to_menu_keyboard, bonuses_keyboard
import database as db

TOMSK_TZ = timezone(timedelta(hours=7))


def _format_history(redemptions: list[dict]) -> str:
    if not redemptions:
        return ""
    lines = ["\n\n\U0001f4cb <b>История списаний:</b>"]
    for r in redemptions[:10]:
        dt = r["created_at"]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(TOMSK_TZ)
        date_str = local.strftime("%d.%m.%Y %H:%M")
        lines.append(f"  \u2022 <b>-{r['amount']}</b> \u2014 {date_str}")
    return "\n".join(lines)


router = Router()


@router.callback_query(SectionCallback.filter(F.name == "bonuses"))
async def show_bonuses(callback: CallbackQuery):
    await callback.answer()
    client = await db.get_client_by_telegram_id(callback.from_user.id)
    if not client:
        await callback.message.answer(
            "\u274c \u041f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 /start",
            reply_markup=back_to_menu_keyboard()
        )
        return

    total = await db.get_client_bonus_total(client["id"])
    promo_code = await db.get_client_promo_code(client["id"])

    if total == 0 and not promo_code:
        await callback.message.answer(
            "У вас пока нет доступных бонусов \U0001f614",
            reply_markup=back_to_menu_keyboard()
        )
        return

    created = client["created_at"]
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    expiry = created.astimezone(TOMSK_TZ) + timedelta(days=14)
    expiry_str = expiry.strftime("%d.%m.%Y")

    redemptions = await db.get_client_redemptions(client["id"])
    history = _format_history(redemptions)

    await callback.message.answer(
        f"\U0001f381 У вас <b>{total}</b> бонусов!\n\n"
        f"Ваш уникальный промокод: <b>{promo_code}</b>\n\n"
        f"Воспользоваться промокодом можно до <b>{expiry_str}</b>\n"
        f"Назовите его на кассе в магазине либо свяжитесь с он-лайн менеджером.{history}",
        parse_mode="HTML",
        reply_markup=bonuses_keyboard()
    )


@router.callback_query(SectionCallback.filter(F.name == "bonus_terms"))
async def show_bonus_terms(callback: CallbackQuery):
    await callback.answer()
    terms = await db.get_setting("bonus_terms")
    text = terms if terms else "Условия будут тут позже."
    await callback.message.answer(
        f"\U0001f4d6 <b>Условия бонусной программы</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard()
    )


@router.callback_query(BonusCallback.filter(F.action == "claim"))
async def claim_bonuses(callback: CallbackQuery):
    """Backward compat for old 'claim' buttons — just show bonuses."""
    await show_bonuses(callback)
