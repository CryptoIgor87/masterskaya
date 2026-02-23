import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest
import uvicorn

from config import BOT_TOKEN, WEB_HOST, WEB_PORT, UPLOADS_DIR
from database import init_db, close_db
from bot.handlers import start, promotions, bonuses, feedback
from bot.middlewares.register import RegisterMiddleware
from web.app import create_app


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Ensure directories exist
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create bot
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Global error handler — ignore stale callback queries
    @dp.errors()
    async def on_error(event: ErrorEvent):
        if isinstance(event.exception, TelegramBadRequest):
            logger.warning(f"TelegramBadRequest (ignored): {event.exception}")
            return True
        return False

    # Register middleware
    dp.update.outer_middleware(RegisterMiddleware())

    # Register handlers
    dp.include_router(start.router)
    dp.include_router(promotions.router)
    dp.include_router(bonuses.router)
    dp.include_router(feedback.router)

    # Create web app
    app = create_app(bot)

    # Run both concurrently
    config = uvicorn.Config(app, host=WEB_HOST, port=WEB_PORT, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"Starting bot polling + web admin at http://{WEB_HOST}:{WEB_PORT}")

    try:
        await asyncio.gather(
            dp.start_polling(bot, drop_pending_updates=True),
            server.serve(),
        )
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
