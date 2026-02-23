from typing import Any, Awaitable, Callable, Dict, Set
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import database as db


class RegisterMiddleware(BaseMiddleware):
    def __init__(self):
        self._known_users: Set[int] = set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and not user.is_bot and user.id not in self._known_users:
            await db.ensure_client_registered(
                telegram_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                language_code=user.language_code,
            )
            self._known_users.add(user.id)
        return await handler(event, data)
