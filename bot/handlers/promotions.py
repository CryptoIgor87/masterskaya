import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from bot.callbacks.callback_data import SectionCallback
from bot.keyboards.main_menu import back_to_menu_keyboard
from config import UPLOADS_DIR
import database as db

router = Router()


@router.callback_query(SectionCallback.filter(F.name == "promotions"))
async def show_promotions(callback: CallbackQuery):
    await callback.answer()
    promotions = await db.get_active_promotions()

    if not promotions:
        await callback.message.answer(
            "Сейчас нет активных акций \U0001f614",
            reply_markup=back_to_menu_keyboard()
        )
        return

    for promo in promotions:
        caption = (
            f"<b>{promo['title']}</b>\n\n"
            f"{promo['description']}\n\n"
            f"\U0001f4c5 Действует: {promo['start_date']} — {promo['end_date']}"
        )
        if promo["photo_path"] and os.path.exists(os.path.join(UPLOADS_DIR, promo["photo_path"])):
            photo = FSInputFile(os.path.join(UPLOADS_DIR, promo["photo_path"]))
            await callback.message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
        else:
            await callback.message.answer(caption, parse_mode="HTML")

    await callback.message.answer(
        "Это все текущие акции!",
        reply_markup=back_to_menu_keyboard()
    )
