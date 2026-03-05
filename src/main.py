import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.config import TELEGRAM_TOKEN, logger
from src.database.connection import init_db
from src.bot.handlers import router

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_TOKEN found. Exiting...")
        sys.exit(1)
        
    logger.info("Initializing Database...")
    await init_db()
    
    logger.info("Initializing Bot...")
    bot = Bot(
        token=TELEGRAM_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(router)
    
    logger.info("Бот запущен и готов к провокациям...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Бот упал с критической ошибкой: {e}", exc_info=True)
