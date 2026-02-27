from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.callbacks.callback_data import SectionCallback, BonusCallback, NavigationCallback
from config import WEBSITE_URL


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="\U0001f381 Ваши бонусы",
        callback_data=SectionCallback(name="bonuses").pack()
    ))
    builder.row(InlineKeyboardButton(
        text="\U0001f4d6 Условия бонусной программы",
        callback_data=SectionCallback(name="bonus_terms").pack()
    ))
    builder.row(InlineKeyboardButton(
        text="\U0001f3f7 Акции",
        callback_data=SectionCallback(name="promotions").pack()
    ))
    builder.row(InlineKeyboardButton(
        text="\u2709\ufe0f Задать вопрос",
        url="tg://resolve?domain=MasterskayaOrders"
    ))
    builder.row(InlineKeyboardButton(
        text="\U0001f310 Сайт магазина",
        url=WEBSITE_URL
    ))
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="\u25c0\ufe0f Назад в меню",
        callback_data=NavigationCallback(action="back_to_menu").pack()
    ))
    return builder.as_markup()


def bonuses_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="\U0001f4ac Он-лайн менеджер",
        url="tg://resolve?domain=MasterskayaOrders"
    ))
    builder.row(InlineKeyboardButton(
        text="\u25c0\ufe0f Назад в меню",
        callback_data=NavigationCallback(action="back_to_menu").pack()
    ))
    return builder.as_markup()
