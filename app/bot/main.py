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
from app.repositories.topic_repository import get_topic_name, save_topic_name
from app.repositories.stats_repository import (
    get_basic_stats,
    get_decision_action_stats,
    get_recent_decisions_with_messages,
    get_topic_stats,
)


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🤖 TAIO está funcionando correctamente.")

@dp.message(Command("adminhelp"))
async def cmd_adminhelp(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar la ayuda de TAIO.")
        return

    await message.answer(
        "🧭 Comandos de administración de TAIO\n\n"
        "/status - Ver configuración actual del bot\n"
        "/readiness - Comprobar si está seguro para grupo grande\n"
        "/health - Comprobar que bot y base de datos responden\n"
        "/stats - Ver mensajes y decisiones guardadas\n"
        "/decisionstats - Ver resumen por tipo de decisión\n"
        "/decisions [n] - Ver últimas decisiones simuladas, máximo 20\n"
        "/whereami - Ver chat_id, thread_id y user_id\n"
        "/chatcheck - Comprobar si este chat está autorizado\n"
        "/entrycheck - Comprobación final antes de observar un grupo\n"
        "/topics - Ver Topics detectados por TAIO\n"
        "/settopic Nombre - Guardar el nombre de un Topic\n"
        "/adminhelp - Ver esta ayuda\n\n"
        "Funciones ya simuladas:\n"
        "- Clasificación básica hacia Topics\n"
        "- Detección de duplicados\n"
        "- Detección de flood\n"
        "- Detección de enlaces\n"
        "- Moderación básica de mayúsculas e insultos\n\n"
        "Estado recomendado para grupo grande:\n"
        "ACTION_MODE=listen\n"
        "ENABLE_DELETES=false\n"
        "ENABLE_REPOSTS=false\n"
        "ENABLE_PRIVATE_NOTICES=false"
    )

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
        f"Chats autorizados configurados: {'✅' if allowed_chats_ok else '❌'} "
        f"({len(ALLOWED_CHAT_IDS)})\n"
        f"Administradores configurados: {'✅' if admins_ok else '❌'} "
        f"({len(ADMIN_USER_IDS)})\n\n"
        f"Resultado: {'✅ LISTO PARA OBSERVAR SIN ACTUAR' if ready else '❌ NO LISTO'}"
    )

@dp.message(Command("health"))
async def cmd_health(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar la salud de TAIO.")
        return

    try:
        stats = await get_basic_stats()

        await message.answer(
            "🩺 Salud de TAIO\n\n"
            "Bot: ✅ funcionando\n"
            "Base de datos: ✅ responde\n"
            f"Mensajes guardados: {stats['messages']}\n"
            f"Decisiones guardadas: {stats['decisions']}\n"
            f"Modo de acción: {ACTION_MODE}"
        )

    except Exception as error:
        logging.exception("Error comprobando salud de TAIO")

        await message.answer(
            "🩺 Salud de TAIO\n\n"
            "Bot: ✅ funcionando\n"
            "Base de datos: ❌ error\n"
            f"Detalle: {type(error).__name__}"
        )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar las estadísticas de TAIO.")
        return

    telegram_chat_id = None if message.chat.type == "private" else message.chat.id

    stats = await get_basic_stats(
        telegram_chat_id=telegram_chat_id,
    )

    scope = "todos los chats" if telegram_chat_id is None else f"chat {telegram_chat_id}"

    await message.answer(
        "📊 Estadísticas de TAIO\n\n"
        f"Ámbito: {scope}\n\n"
        f"Mensajes guardados: {stats['messages']}\n"
        f"Decisiones guardadas: {stats['decisions']}"
    )

@dp.message(Command("decisionstats"))
async def cmd_decisionstats(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar el resumen de decisiones de TAIO.")
        return

    telegram_chat_id = None if message.chat.type == "private" else message.chat.id

    stats = await get_decision_action_stats(
        telegram_chat_id=telegram_chat_id,
    )

    if not stats:
        await message.answer("TAIO todavía no tiene decisiones guardadas.")
        return

    scope = "todos los chats" if telegram_chat_id is None else f"chat {telegram_chat_id}"

    lines = [f"📈 Resumen de decisiones de TAIO\n\nÁmbito: {scope}\n"]

    for item in stats:
        lines.append(
            f"{item['action']}: {item['count']}"
        )

    await message.answer("\n".join(lines))

@dp.message(Command("decisions"))
async def cmd_decisions(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar las decisiones de TAIO.")
        return

    parts = (message.text or "").split(maxsplit=1)

    limit = 5

    if len(parts) > 1:
        try:
            limit = int(parts[1])
        except ValueError:
            await message.answer("Uso correcto: /decisions o /decisions 10")
            return

    limit = max(1, min(limit, 20))

    telegram_chat_id = None if message.chat.type == "private" else message.chat.id

    items = await get_recent_decisions_with_messages(
        limit=limit,
        telegram_chat_id=telegram_chat_id,
    )

    if not items:
        await message.answer("TAIO todavía no tiene decisiones guardadas.")
        return

    scope = "todos los chats" if telegram_chat_id is None else f"chat {telegram_chat_id}"

    lines = [f"🧠 Últimas decisiones de TAIO\n\nÁmbito: {scope}\n"]

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

@dp.message(Command("chatcheck"))
async def cmd_chatcheck(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para comprobar este chat.")
        return

    chat_allowed = is_allowed_chat(message.chat.id)
    admin_allowed = is_admin_user(message.from_user.id if message.from_user else None)

    await message.answer(
        "🔎 Comprobación del chat\n\n"
        f"Chat ID: {message.chat.id}\n"
        f"Tipo de chat: {message.chat.type}\n"
        f"Thread ID: {message.message_thread_id}\n"
        f"Chat autorizado: {'✅' if chat_allowed else '❌'}\n"
        f"Usuario admin: {'✅' if admin_allowed else '❌'}"
    )

@dp.message(Command("entrycheck"))
async def cmd_entrycheck(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para hacer la comprobación de entrada.")
        return

    safe_mode_ok = ACTION_MODE == "listen"
    deletes_ok = not ENABLE_DELETES
    reposts_ok = not ENABLE_REPOSTS
    notices_ok = not ENABLE_PRIVATE_NOTICES
    chat_allowed = is_allowed_chat(message.chat.id)
    admin_allowed = is_admin_user(message.from_user.id if message.from_user else None)

    telegram_chat_id = None if message.chat.type == "private" else message.chat.id

    try:
        stats = await get_basic_stats(
            telegram_chat_id=telegram_chat_id,
        )
        database_ok = True
    except Exception:
        logging.exception("Error comprobando base de datos en entrycheck")
        stats = {"messages": 0, "decisions": 0}
        database_ok = False

    ready = all(
        [
            safe_mode_ok,
            deletes_ok,
            reposts_ok,
            notices_ok,
            chat_allowed,
            admin_allowed,
            database_ok,
        ]
    )

    await message.answer(
        "🚦 Comprobación de entrada de TAIO\n\n"
        f"Chat ID: {message.chat.id}\n"
        f"Tipo de chat: {message.chat.type}\n"
        f"Thread ID: {message.message_thread_id}\n\n"
        f"Bot funcionando: ✅\n"
        f"Base de datos responde: {'✅' if database_ok else '❌'}\n"
        f"Chat autorizado: {'✅' if chat_allowed else '❌'}\n"
        f"Usuario admin: {'✅' if admin_allowed else '❌'}\n"
        f"Modo escucha activo: {'✅' if safe_mode_ok else '❌'}\n"
        f"Borrados desactivados: {'✅' if deletes_ok else '❌'}\n"
        f"Reenvíos desactivados: {'✅' if reposts_ok else '❌'}\n"
        f"Avisos privados desactivados: {'✅' if notices_ok else '❌'}\n\n"
        f"Ámbito estadísticas: {'todos los chats' if telegram_chat_id is None else f'chat {telegram_chat_id}'}\n"
        f"Mensajes guardados: {stats['messages']}\n"
        f"Decisiones guardadas: {stats['decisions']}\n\n"
        f"Resultado: {'✅ APTO PARA OBSERVAR SIN ACTUAR' if ready else '❌ NO APTO TODAVÍA'}"
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
        topic_name = await get_topic_name(message.chat.id, topic["thread_id"])
        display_name = topic_name or f"Topic {topic['thread_id']}"

        lines.append(
            f"Nombre: {display_name}\n"
            f"Thread ID: {topic['thread_id']}\n"
            f"Mensajes guardados: {topic['messages']}\n"
            f"Último mensaje: {topic['last_message_at']}\n"
        )

    await message.answer("\n".join(lines))

@dp.message(Command("settopic"))
async def cmd_settopic(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para configurar Topics en TAIO.")
        return

    if message.message_thread_id is None:
        await message.answer(
            "Este comando debe usarse dentro de un Topic, no en General ni en privado."
        )
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Uso correcto: /settopic Nombre del Topic")
        return

    topic_name = parts[1].strip()

    await save_topic_name(
        telegram_chat_id=message.chat.id,
        thread_id=message.message_thread_id,
        name=topic_name,
    )

    await message.answer(
        f"✅ Topic guardado en TAIO\n\n"
        f"Thread ID: {message.message_thread_id}\n"
        f"Nombre: {topic_name}"
    )

@dp.message()
async def capture_message(message: Message):
    if message.text and message.text.strip().startswith("/"):
        logging.info(
            f"Comando ignorado por capturador general: "
            f"chat={message.chat.id}, message={message.message_id}"
        )
        return

    if message.from_user and message.from_user.is_bot:
        logging.info(
            f"Mensaje de bot ignorado: "
            f"chat={message.chat.id}, message={message.message_id}"
        )
        return
    
    has_useful_content = bool(
        message.text
        or message.caption
        or message.photo
        or message.video
        or message.document
    )

    if not has_useful_content:
        logging.info(
            f"Mensaje sin contenido útil ignorado: "
            f"chat={message.chat.id}, message={message.message_id}"
        )
        return
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