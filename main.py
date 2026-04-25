import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from handlers import start_router, platform_router

logging.basicConfig(level=logging.INFO)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="▶️ Запустить / перезапустить бота"),
        BotCommand(command="stop", description="⏹️ Остановить бота"),
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(platform_router)

    await set_bot_commands(bot)
    logging.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")