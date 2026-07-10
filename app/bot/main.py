import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config.settings import (
    ACTION_MODE,
    ADMIN_USER_IDS,
    ALLOWED_CHAT_IDS,
    BOT_TOKEN,
    ENABLE_DELETES,
    ENABLE_PRIVATE_NOTICES,
    ENABLE_REPOSTS,
    SIMULATION_MODE,
    is_admin_user,
    is_allowed_chat,
)
from app.database.init_db import init_db
from app.repositories.decision_repository import save_decision
from app.repositories.message_repository import save_message
from app.services.decision_engine import decide_for_message
from app.services.message_parser import parse_message
from app.services.action_executor import execute_decision
from app.repositories.stats_repository import (
    get_basic_stats,
    get_recent_decisions_with_messages,
    get_topic_stats,
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🤖 TAIO está funcionando correctamente.")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar el estado de TAIO.")
        return

    allowed_chats = ", ".join(str(chat_id) for chat_id in ALLOWED_CHAT_IDS) or "ninguno"

    await message.answer(
        "🤖 Estado de TAIO\n\n"
        f"Modo simulación: {SIMULATION_MODE}\n"
        f"Modo de acción: {ACTION_MODE}\n"
        f"Borrados habilitados: {ENABLE_DELETES}\n"
        f"Reenvíos habilitados: {ENABLE_REPOSTS}\n"
        f"Avisos privados habilitados: {ENABLE_PRIVATE_NOTICES}\n"
        f"Chats autorizados: {allowed_chats}"
    )

@dp.message(Command("readiness"))
async def cmd_readiness(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar la preparación de TAIO.")
        return

    safe_mode_ok = ACTION_MODE == "listen"
    deletes_ok = not ENABLE_DELETES
    reposts_ok = not ENABLE_REPOSTS
    notices_ok = not ENABLE_PRIVATE_NOTICES
    allowed_chats_ok = bool(ALLOWED_CHAT_IDS)
    admins_ok = bool(ADMIN_USER_IDS)

    ready = all(
        [
            safe_mode_ok,
            deletes_ok,
            reposts_ok,
            notices_ok,
            allowed_chats_ok,
            admins_ok,
        ]
    )

    await message.answer(
        "🛡️ Preparación de TAIO para grupo grande\n\n"
        f"Modo escucha activo: {'✅' if safe_mode_ok else '❌'}\n"
        f"Borrados desactivados: {'✅' if deletes_ok else '❌'}\n"
        f"Reenvíos desactivados: {'✅' if reposts_ok else '❌'}\n"
        f"Avisos privados desactivados: {'✅' if notices_ok else '❌'}\n"
        f"Chats autorizados configurados: {'✅' if allowed_chats_ok else '❌'}\n"
        f"Administradores configurados: {'✅' if admins_ok else '❌'}\n\n"
        f"Resultado: {'✅ LISTO PARA OBSERVAR SIN ACTUAR' if ready else '❌ NO LISTO'}"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar las estadísticas de TAIO.")
        return

    stats = await get_basic_stats()

    await message.answer(
        "📊 Estadísticas de TAIO\n\n"
        f"Mensajes guardados: {stats['messages']}\n"
        f"Decisiones guardadas: {stats['decisions']}"
    )

@dp.message(Command("decisions"))
async def cmd_decisions(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar las decisiones de TAIO.")
        return

    items = await get_recent_decisions_with_messages(limit=5)

    if not items:
        await message.answer("TAIO todavía no tiene decisiones guardadas.")
        return

    lines = ["🧠 Últimas decisiones de TAIO\n"]

    for item in items:
        decision = item["decision"]
        stored_message = item["message"]

        if stored_message and stored_message.text:
            text_preview = stored_message.text[:120]
        else:
            text_preview = "sin texto"

        if stored_message:
            thread_info = (
                "General"
                if stored_message.thread_id is None
                else f"Topic {stored_message.thread_id}"
            )
        else:
            thread_info = "desconocido"

        lines.append(
            f"Mensaje {decision.telegram_message_id} · {thread_info}\n"
            f"Texto: {text_preview}\n"
            f"Acción: {decision.action}\n"
            f"Confianza: {decision.confidence:.2%}\n"
            f"Motivo: {decision.reason}\n"
        )

    await message.answer("\n".join(lines))

@dp.message(Command("whereami"))
async def cmd_whereami(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar esta información.")
        return

    await message.answer(
        "📍 Información del chat\n\n"
        f"Chat ID: {message.chat.id}\n"
        f"Tipo de chat: {message.chat.type}\n"
        f"Thread ID: {message.message_thread_id}\n"
        f"Tu user ID: {message.from_user.id if message.from_user else 'desconocido'}"
    )

@dp.message(Command("topics"))
async def cmd_topics(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar los Topics de TAIO.")
        return

    topics = await get_topic_stats(message.chat.id)

    if not topics:
        await message.answer("TAIO todavía no tiene mensajes guardados en Topics.")
        return

    lines = ["🧵 Topics detectados por TAIO\n"]

    for topic in topics:
        lines.append(
            f"Thread ID: {topic['thread_id']}\n"
            f"Mensajes guardados: {topic['messages']}\n"
            f"Último mensaje: {topic['last_message_at']}\n"
        )

    await message.answer("\n".join(lines))

@dp.message()
async def capture_message(message: Message):
    if not is_allowed_chat(message.chat.id):
        logging.warning(f"Chat no autorizado ignorado: {message.chat.id}")
        return

    try:
        msg = parse_message(message)

        logging.info(
            f"Mensaje recibido: chat={msg.telegram_chat_id}, "
            f"thread={msg.thread_id}, message={msg.telegram_message_id}, "
            f"user={msg.user_id}"
        )

        await save_message(msg)

        logging.info(
            f"Mensaje guardado: chat={msg.telegram_chat_id}, "
            f"message={msg.telegram_message_id}"
        )

        decision = await decide_for_message(msg)
        await save_decision(msg, decision)
        await execute_decision(msg, decision)

        logging.info(
            f"Decisión simulada: message={msg.telegram_message_id}, "
            f"action={decision.action}, "
            f"confidence={decision.confidence:.2%}"
        )

    except Exception:
        logging.exception(
            f"Error procesando mensaje de Telegram: "
            f"chat_id={message.chat.id}, message_id={message.message_id}"
        )

async def main():
    logging.info("Inicializando base de datos...")
    await init_db()

    logging.info("Iniciando TAIO...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())