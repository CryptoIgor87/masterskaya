from aiogram.filters.callback_data import CallbackData


class SectionCallback(CallbackData, prefix="section"):
    name: str  # "promotions", "bonuses", "feedback"


class BonusCallback(CallbackData, prefix="bonus"):
    action: str  # "claim"


class FeedbackReplyCallback(CallbackData, prefix="fb_reply"):
    feedback_id: int


class NavigationCallback(CallbackData, prefix="nav"):
    action: str  # "back_to_menu"


class GiveawayCaptchaCallback(CallbackData, prefix="gw_captcha"):
    giveaway_id: int
    answer: int
