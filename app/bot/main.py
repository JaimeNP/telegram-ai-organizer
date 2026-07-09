import asyncio
import logging
from app.repositories.decision_repository import save_decision
from app.services.decision_engine import decide_for_message
from app.moderation.rules import check_message_rules
from app.services.duplicate_detector import detect_duplicate

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config.settings import BOT_TOKEN
from app.database.init_db import init_db
from app.repositories.message_repository import save_message
from app.services.message_parser import parse_message

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🤖 TAIO está funcionando correctamente.")


@dp.message()
async def capture_message(message: Message):
    msg = parse_message(message)

    logging.warning(f"Guardando mensaje: {msg}")
    await save_message(msg)
    logging.warning("Mensaje guardado correctamente en PostgreSQL")

    decision = await decide_for_message(msg)
    await save_decision(msg, decision)

    logging.warning(
        f"Decisión simulada: action={decision.action}, "
        f"confidence={decision.confidence:.2%}, reason={decision.reason}"
    )



async def main():
    logging.info("Inicializando base de datos...")
    await init_db()

    logging.info("Iniciando TAIO...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())