import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
from app.repositories.topic_repository import (
    get_topic_info,
    get_topic_name,
    mark_topic_closed,
    mark_topic_reopened,
    mark_topic_seen,
    save_topic_name,
)
from app.services.topic_keyword_classifier import classify_topic_by_keywords
from app.repositories.learning_repository import (
    get_message_by_telegram_id,
    save_learning_example,
)
from app.services.learning_classifier import classify_topic_by_learning
from app.repositories.stats_repository import (
    get_basic_stats,
    get_decision_action_stats,
    get_recent_decisions_by_action,
    get_recent_decisions_with_messages,
    get_recent_general_messages_with_decisions,
    get_topic_message_samples,
    get_topic_samples,
    get_topic_stats,
)


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AdminOnly(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return is_admin_user(message.from_user.id if message.from_user else None)

def build_telegram_message_link(
    telegram_chat_id: int,
    telegram_message_id: int,
) -> str | None:
    chat_id = str(telegram_chat_id)

    if chat_id.startswith("-100"):
        internal_chat_id = chat_id[4:]
        return f"https://t.me/c/{internal_chat_id}/{telegram_message_id}"

    return None

AIRBUS_TRIAGE_TOPIC_BUTTONS = [
    (9482, "Propuestas"),
    (21638, "Documentación"),
    (21630, "Comité Huelga"),
    (21634, "Comunicación"),
    (14577, "Medios/redes"),
    (3302, "Comunicados"),
    (9628, "Manifestaciones"),
    (15949, "Éxitos huelga"),
    (20559, "Grupos Trabajo"),
    (5338, "Eslogan"),
    (3320, "Archivo/docs"),
    (19265, "Jean Brice"),
]


def build_learning_keyboard(
    telegram_chat_id: int,
    telegram_message_id: int,
    target_thread_id: int,
    topic_name: str,
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"✅ Mover a {topic_name[:28]}",
                callback_data=(
                    f"learn:move:{telegram_chat_id}:"
                    f"{telegram_message_id}:{target_thread_id}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Dejar en General",
                callback_data=(
                    f"learn:allow:{telegram_chat_id}:"
                    f"{telegram_message_id}"
                ),
            )
        ],
    ]

    if telegram_chat_id == -1003710195540:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="👇 Mover a otro Topic",
                    callback_data=(
                        f"learn:noop:{telegram_chat_id}:"
                        f"{telegram_message_id}"
                    ),
                )
            ]
        )

        alternative_buttons = []

        for thread_id, label in AIRBUS_TRIAGE_TOPIC_BUTTONS:
            if thread_id == target_thread_id:
                continue

            alternative_buttons.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        f"learn:move:{telegram_chat_id}:"
                        f"{telegram_message_id}:{thread_id}"
                    ),
                )
            )

        for index in range(0, len(alternative_buttons), 2):
            keyboard.append(alternative_buttons[index:index + 2])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("🤖 TAIO está funcionando correctamente.")

@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    user_id = message.from_user.id if message.from_user else None
    username = message.from_user.username if message.from_user else None

    await message.answer(
        "🪪 Tu identificador de Telegram\n\n"
        f"User ID: {user_id}\n"
        f"Username: @{username if username else 'sin_username'}\n\n"
        "Pásale este User ID al administrador de TAIO para que pueda darte acceso."
    )

@dp.message(Command("adminhelp"), AdminOnly())
async def cmd_adminhelp(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        await message.answer("No tienes permiso para consultar la ayuda de TAIO.")
        return

    await message.answer(
        "🧭 Comandos de administración de TAIO\n\n"
       "/myid - Ver tu User ID de Telegram\n"
        "/status - Ver configuración actual del bot\n"
        "/readiness - Comprobar si está seguro para grupo grande\n"
        "/health - Comprobar que bot y base de datos responden\n"
        "/stats - Ver mensajes y decisiones guardadas\n"
        "/decisionstats - Ver resumen por tipo de decisión\n"
        "/decisions [n] - Ver últimas decisiones simuladas, máximo 20\n"
        "/moves CHAT_ID [n] - Ver sugerencias de movimiento a Topics\n"
       "/general CHAT_ID [n] - Ver mensajes recientes de General\n"
       "/triage CHAT_ID [n] - Sugerir Topics para mensajes recientes de General\n"
       "/triagecards CHAT_ID [n] - Triage con botones para aprender\n"
        "/learnmove CHAT_ID MESSAGE_ID THREAD_ID - Enseñar movimiento correcto\n"
        "/learnallow CHAT_ID MESSAGE_ID - Enseñar que puede quedarse en General\n"
        "/whereami - Ver chat_id, thread_id y user_id\n"
        "/chatcheck - Comprobar si este chat está autorizado\n"
        "/entrycheck - Comprobación final antes de observar un grupo\n"
        "/topics [CHAT_ID] - Ver Topics detectados\n"
        "/topicsamples CHAT_ID [n] - Ver muestras por Topic, máximo 5\n"
        "/topicdetail CHAT_ID THREAD_ID [n] - Ver muestras de un Topic concreto\n"
        "/settopic Nombre - Guardar el nombre desde dentro de un Topic\n"
        "/settopicid CHAT_ID THREAD_ID Nombre - Guardar nombre desde privado\n"
        "/adminhelp - Ver esta ayuda\n\n"
        "/adminbrief - Resumen rápido para admins nuevos\n"
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


@dp.message(Command("adminbrief"), AdminOnly())
async def cmd_adminbrief(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        "🧭 Resumen rápido de TAIO para admins\n\n"
        "Estado actual:\n"
        "- TAIO observa Airbus en modo seguro.\n"
        "- No borra mensajes.\n"
        "- No mueve mensajes.\n"
        "- No escribe avisos privados.\n"
        "- Solo propone y aprende.\n\n"
        "Uso recomendado siempre por privado con @taio_airbus_bot.\n\n"
        "1) Revisar mensajes recientes de General:\n"
        "/triage -1003710195540 30\n\n"
        "2) Si TAIO acierta, copiar el comando que aparece bajo:\n"
        "✅ Confirmar\n\n"
        "Ejemplo:\n"
        "/learnmove -1003710195540 22585 9482\n\n"
        "3) Si TAIO se equivoca, copiar el comando bajo:\n"
        "❌ Dejar en General\n\n"
        "Ejemplo:\n"
        "/learnallow -1003710195540 22585\n\n"
        "4) Ver Topics conocidos:\n"
        "/topics -1003710195540\n\n"
        "5) Ver mensajes recientes de General:\n"
        "/general -1003710195540 20\n\n"
        "Importante:\n"
        "- No hace falta ser admin del grupo de Telegram para enseñar a TAIO ahora mismo.\n"
        "- No usar comandos dentro del grupo Airbus salvo necesidad.\n"
        "- Si hay duda, usar /learnallow antes que forzar un Topic incorrecto."
    )

@dp.message(Command("status"), AdminOnly())
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
        f"Chats autorizados: {allowed_chats}\n"
        f"Número de chats autorizados: {len(ALLOWED_CHAT_IDS)}\n"
        f"Número de admins configurados: {len(ADMIN_USER_IDS)}"
    )

@dp.message(Command("readiness"), AdminOnly())
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

@dp.message(Command("health"), AdminOnly())
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

@dp.message(Command("stats"), AdminOnly())
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

@dp.message(Command("decisionstats"), AdminOnly())
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

@dp.message(Command("decisions"), AdminOnly())
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
            text_preview = " ".join(stored_message.text.split())
            text_preview = text_preview[:60]
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

        reason_preview = " ".join(decision.reason.split())
        reason_preview = reason_preview[:120]

        lines.append(
            f"#{decision.telegram_message_id} · {thread_info}\n"
            f"{decision.action} · {decision.confidence:.0%}\n"
            f"Texto: {text_preview}\n"
            f"Motivo: {reason_preview}\n"
        )

    await message.answer("\n".join(lines))

@dp.message(Command("moves"), AdminOnly())
async def cmd_moves(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    limit = 10

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /moves CHAT_ID [n]")
            return

        try:
            telegram_chat_id = int(parts[1])
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                limit = int(parts[2])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return
    else:
        telegram_chat_id = message.chat.id

        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return

    limit = max(1, min(limit, 20))

    rows = await get_recent_decisions_by_action(
        action="would_move_to_topic",
        telegram_chat_id=telegram_chat_id,
        limit=limit,
    )

    if not rows:
        await message.answer("No hay sugerencias de movimiento registradas.")
        return

    lines = [
        "🚚 Sugerencias de movimiento\n",
        f"Chat: {telegram_chat_id}",
        f"Límite: {limit}\n",
    ]

    for row in rows:
        decision = row["decision"]
        stored_message = row["message"]

        text_preview = ""

        if stored_message and stored_message.text:
            text_preview = " ".join(stored_message.text.split())[:140]
        else:
            text_preview = "[mensaje sin texto]"

        message_link = build_telegram_message_link(
            telegram_chat_id=decision.telegram_chat_id,
            telegram_message_id=decision.telegram_message_id,
        )

        lines.append(
            f"#{decision.telegram_message_id} · {decision.confidence:.0%}\n"
            f"Texto: {text_preview}\n"
            f"Motivo: {decision.reason[:180]}"
        )

        if message_link:
            lines.append(message_link)

        lines.append("")

    await message.answer("\n".join(lines))

@dp.message(Command("general"), AdminOnly())
async def cmd_general(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    limit = 10

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /general CHAT_ID [n]")
            return

        try:
            telegram_chat_id = int(parts[1])
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                limit = int(parts[2])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return
    else:
        telegram_chat_id = message.chat.id

        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return

    limit = max(1, min(limit, 20))

    rows = await get_recent_general_messages_with_decisions(
        telegram_chat_id=telegram_chat_id,
        limit=limit,
    )

    if not rows:
        await message.answer("No hay mensajes recientes en General.")
        return

    lines = [
        "🧭 Mensajes recientes en General\n",
        f"Chat: {telegram_chat_id}",
        f"Límite: {limit}\n",
    ]

    for row in rows:
        stored_message = row["message"]
        decision = row["decision"]

        text_preview = " ".join((stored_message.text or "").split())

        if text_preview:
            text_preview = text_preview[:180]
        else:
            content_types = []

            if stored_message.has_photo:
                content_types.append("foto")

            if stored_message.has_video:
                content_types.append("vídeo")

            if stored_message.has_document:
                content_types.append("documento")

            if not content_types:
                content_types.append("mensaje sin texto")

            text_preview = "[" + ", ".join(content_types) + "]"

        if decision:
            decision_text = f"{decision.action} · {decision.confidence:.0%}"
        else:
            decision_text = "sin decisión registrada"

        message_link = build_telegram_message_link(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=stored_message.telegram_message_id,
        )

        lines.append(
            f"#{stored_message.telegram_message_id} · {decision_text}\n"
            f"Texto: {text_preview}"
        )

        if message_link:
            lines.append(message_link)

        lines.append("")

    await message.answer("\n".join(lines))

@dp.message(Command("triage"), AdminOnly())
async def cmd_triage(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    limit = 30

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /triage CHAT_ID [n]")
            return

        try:
            telegram_chat_id = int(parts[1])
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                limit = int(parts[2])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return
    else:
        telegram_chat_id = message.chat.id

        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return

    limit = max(1, min(limit, 50))

    rows = await get_recent_general_messages_with_decisions(
        telegram_chat_id=telegram_chat_id,
        limit=limit,
    )

    suggestions = []

    for row in rows:
        stored_message = row["message"]
        learning_match = await classify_topic_by_learning(stored_message)

        if learning_match.should_stay_in_general:
            continue

        if learning_match.should_move:
            suggestions.append(
                {
                    "message": stored_message,
                    "match": learning_match,
                }
            )
            continue

        match = classify_topic_by_keywords(stored_message)

        if match.should_move:
            suggestions.append(
                {
                    "message": stored_message,
                    "match": match,
                }
            )

    if not suggestions:
        await message.answer("No hay sugerencias de Topic para General.")
        return

    lines = [
        "🚦 Triage de General\n",
        f"Chat: {telegram_chat_id}",
        f"Mensajes revisados: {limit}",
        f"Sugerencias: {len(suggestions)}\n",
    ]

    for item in suggestions[:15]:
        stored_message = item["message"]
        match = item["match"]

        target_thread_id = match.target_thread_id

        topic_info = await get_topic_info(
            telegram_chat_id,
            target_thread_id,
        )

        topic_display = (
            topic_info.name
            if topic_info
            else f"Topic {target_thread_id}"
        )

        topic_status = ""

        if topic_info and topic_info.is_closed:
            topic_status = " · ⚠️ cerrado"

        if topic_info and topic_info.is_deleted:
            topic_status = " · ⚠️ borrado"

        keywords = ", ".join(match.matched_keywords or [])

        text_preview = " ".join((stored_message.text or "").split())
        text_preview = text_preview[:160] if text_preview else "[mensaje sin texto]"

        message_link = build_telegram_message_link(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=stored_message.telegram_message_id,
        )

        learnmove_command = (
            f"/learnmove {telegram_chat_id} "
            f"{stored_message.telegram_message_id} {target_thread_id}"
        )

        learnallow_command = (
            f"/learnallow {telegram_chat_id} "
            f"{stored_message.telegram_message_id}"
        )

        lines.append(
            f"#{stored_message.telegram_message_id} · {match.confidence:.0%}\n"
            f"Sugerencia: {topic_display}{topic_status}\n"
            f"Claves: {keywords}\n"
            f"Texto: {text_preview}"
        )

        if message_link:
            lines.append(message_link)

        lines.append(
            "\n✅ Confirmar:\n"
            f"{learnmove_command}\n\n"
            "❌ Dejar en General:\n"
            f"{learnallow_command}"
        )

        lines.append("")

    if len(suggestions) > 15:
        lines.append(f"Mostrando 15 de {len(suggestions)} sugerencias.")

    await message.answer("\n".join(lines))


@dp.message(Command("triagecards"), AdminOnly())
async def cmd_triagecards(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    limit = 5

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /triagecards CHAT_ID [n]")
            return

        try:
            telegram_chat_id = int(parts[1])
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                limit = int(parts[2])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return
    else:
        telegram_chat_id = message.chat.id

        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                await message.answer("El límite debe ser un número.")
                return

    limit = max(1, min(limit, 10))

    rows = await get_recent_general_messages_with_decisions(
        telegram_chat_id=telegram_chat_id,
        limit=50,
    )

    suggestions = []

    for row in rows:
        stored_message = row["message"]

        learning_match = await classify_topic_by_learning(stored_message)

        if learning_match.should_stay_in_general:
            continue

        if learning_match.should_move:
            suggestions.append(
                {
                    "message": stored_message,
                    "match": learning_match,
                }
            )
            continue

        match = classify_topic_by_keywords(stored_message)

        if match.should_move:
            suggestions.append(
                {
                    "message": stored_message,
                    "match": match,
                }
            )

    if not suggestions:
        await message.answer("No hay sugerencias de Topic para General.")
        return

    await message.answer(
        f"🚦 Enviando {min(limit, len(suggestions))} tarjetas de triage..."
    )

    for item in suggestions[:limit]:
        stored_message = item["message"]
        match = item["match"]

        target_thread_id = match.target_thread_id

        topic_info = await get_topic_info(
            telegram_chat_id,
            target_thread_id,
        )

        topic_display = (
            topic_info.name
            if topic_info
            else f"Topic {target_thread_id}"
        )

        topic_status = ""

        if topic_info and topic_info.is_closed:
            topic_status = " · ⚠️ cerrado"

        if topic_info and topic_info.is_deleted:
            topic_status = " · ⚠️ borrado"

        keywords = ", ".join(match.matched_keywords or [])

        text_preview = " ".join((stored_message.text or "").split())
        text_preview = text_preview[:700] if text_preview else "[mensaje sin texto]"

        message_link = build_telegram_message_link(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=stored_message.telegram_message_id,
        )

        lines = [
            "🚦 Triage de General",
            "",
            f"Mensaje: #{stored_message.telegram_message_id}",
            f"Sugerencia: {topic_display}{topic_status}",
            f"Confianza: {match.confidence:.0%}",
            f"Claves: {keywords}",
            "",
            f"Texto:\n{text_preview}",
        ]

        if message_link:
            lines.extend(
                [
                    "",
                    message_link,
                ]
            )

        await message.answer(
            "\n".join(lines),
            reply_markup=build_learning_keyboard(
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=stored_message.telegram_message_id,
                target_thread_id=target_thread_id,
                topic_name=topic_display,
            ),
        )

@dp.message(Command("learnmove"), AdminOnly())
async def cmd_learnmove(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    if len(parts) < 4:
        await message.answer("Uso correcto: /learnmove CHAT_ID MESSAGE_ID THREAD_ID")
        return

    try:
        telegram_chat_id = int(parts[1])
        telegram_message_id = int(parts[2])
        target_thread_id = int(parts[3])
    except ValueError:
        await message.answer("CHAT_ID, MESSAGE_ID y THREAD_ID deben ser números.")
        return

    stored_message = await get_message_by_telegram_id(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
    )

    if not stored_message:
        await message.answer("No encuentro ese mensaje en la base de datos.")
        return

    await save_learning_example(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
        source_thread_id=stored_message.thread_id,
        label="move_to_topic",
        target_thread_id=target_thread_id,
        text=stored_message.text,
        created_by_user_id=message.from_user.id if message.from_user else None,
    )

    topic_name = await get_topic_name(
        telegram_chat_id,
        target_thread_id,
    )

    topic_display = topic_name or f"Topic {target_thread_id}"

    text_preview = " ".join((stored_message.text or "").split())
    text_preview = text_preview[:160] if text_preview else "[mensaje sin texto]"

    await message.answer(
        "✅ Aprendizaje guardado\n\n"
        f"Mensaje: #{telegram_message_id}\n"
        f"Debe ir a: {topic_display}\n"
        f"Texto: {text_preview}"
    )


@dp.message(Command("learnallow"), AdminOnly())
async def cmd_learnallow(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    if len(parts) < 3:
        await message.answer("Uso correcto: /learnallow CHAT_ID MESSAGE_ID")
        return

    try:
        telegram_chat_id = int(parts[1])
        telegram_message_id = int(parts[2])
    except ValueError:
        await message.answer("CHAT_ID y MESSAGE_ID deben ser números.")
        return

    stored_message = await get_message_by_telegram_id(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
    )

    if not stored_message:
        await message.answer("No encuentro ese mensaje en la base de datos.")
        return

    await save_learning_example(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
        source_thread_id=stored_message.thread_id,
        label="allow_general",
        target_thread_id=None,
        text=stored_message.text,
        created_by_user_id=message.from_user.id if message.from_user else None,
    )

    text_preview = " ".join((stored_message.text or "").split())
    text_preview = text_preview[:160] if text_preview else "[mensaje sin texto]"

    await message.answer(
        "✅ Aprendizaje guardado\n\n"
        f"Mensaje: #{telegram_message_id}\n"
        "Decisión: puede quedarse en General\n"
        f"Texto: {text_preview}"
    )


@dp.callback_query(lambda callback: callback.data and callback.data.startswith("learn:"))
async def callback_learning(callback: CallbackQuery):
    if not is_admin_user(callback.from_user.id if callback.from_user else None):
        await callback.answer("No tienes permiso para usar TAIO.", show_alert=True)
        return

    data = callback.data or ""
    parts = data.split(":")

    if len(parts) < 4:
        await callback.answer("Acción no válida.", show_alert=True)
        return

    action = parts[1]

    try:
        telegram_chat_id = int(parts[2])
        telegram_message_id = int(parts[3])
    except ValueError:
        await callback.answer("Datos inválidos.", show_alert=True)
        return

    stored_message = await get_message_by_telegram_id(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
    )

    if not stored_message:
        await callback.answer("No encuentro ese mensaje.", show_alert=True)
        return
    if action == "noop":
        await callback.answer(
            "Elige uno de los Topics alternativos.",
            show_alert=False,
        )
        return
    if action == "move":
        if len(parts) < 5:
            await callback.answer("Falta el Topic destino.", show_alert=True)
            return

        try:
            target_thread_id = int(parts[4])
        except ValueError:
            await callback.answer("Topic destino inválido.", show_alert=True)
            return

        await save_learning_example(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            source_thread_id=stored_message.thread_id,
            label="move_to_topic",
            target_thread_id=target_thread_id,
            text=stored_message.text,
            created_by_user_id=callback.from_user.id if callback.from_user else None,
        )

        topic_name = await get_topic_name(
            telegram_chat_id,
            target_thread_id,
        )

        topic_display = topic_name or f"Topic {target_thread_id}"

        await callback.answer("Aprendizaje guardado.")

        if callback.message:
            await callback.message.edit_text(
                (callback.message.text or "")
                + f"\n\n✅ Confirmado por admin: mover a {topic_display}."
            )

        return

    if action == "allow":
        await save_learning_example(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            source_thread_id=stored_message.thread_id,
            label="allow_general",
            target_thread_id=None,
            text=stored_message.text,
            created_by_user_id=callback.from_user.id if callback.from_user else None,
        )

        await callback.answer("Aprendizaje guardado.")

        if callback.message:
            await callback.message.edit_text(
                (callback.message.text or "")
                + "\n\n❌ Confirmado por admin: puede quedarse en General."
            )

        return

    await callback.answer("Acción no reconocida.", show_alert=True)

@dp.message(Command("whereami"), AdminOnly())
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

@dp.message(Command("chatcheck"), AdminOnly())
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

@dp.message(Command("entrycheck"), AdminOnly())
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

@dp.message(Command("topics"), AdminOnly())
async def cmd_topics(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split(maxsplit=1)

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /topics CHAT_ID")
            return

        try:
            telegram_chat_id = int(parts[1].strip())
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return
    else:
        telegram_chat_id = message.chat.id

    topics = await get_topic_stats(telegram_chat_id)

    if not topics:
        await message.answer("Todavía no hay Topics registrados para ese chat.")
        return

    lines = [
        "📌 Topics detectados\n",
        f"Chat: {telegram_chat_id}\n",
    ]

    for topic in topics[:50]:
        topic_info = await get_topic_info(
            telegram_chat_id,
            topic["thread_id"],
        )

        display_name = (
            topic_info.name
            if topic_info
            else f"Topic {topic['thread_id']}"
        )

        status_parts = []

        if topic_info and topic_info.is_closed:
            status_parts.append("cerrado")

        if topic_info and topic_info.is_deleted:
            status_parts.append("borrado")

        status_text = ""

        if status_parts:
            status_text = " · " + ", ".join(status_parts)

        lines.append(
            f"{display_name} · ID {topic['thread_id']} · "
            f"{topic['messages']} mensajes{status_text}"
        )

    if len(topics) > 50:
        lines.append(f"\nMostrando 50 de {len(topics)} Topics detectados.")

    await message.answer("\n".join(lines))

@dp.message(Command("topicsamples"), AdminOnly())
async def cmd_topicsamples(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    samples_per_topic = 2

    if message.chat.type == "private":
        if len(parts) < 2:
            await message.answer("Uso correcto: /topicsamples CHAT_ID [muestras_por_topic]")
            return

        try:
            telegram_chat_id = int(parts[1])
        except ValueError:
            await message.answer("El CHAT_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                samples_per_topic = int(parts[2])
            except ValueError:
                await message.answer("El número de muestras debe ser un número.")
                return
    else:
        telegram_chat_id = message.chat.id

        if len(parts) >= 2:
            try:
                samples_per_topic = int(parts[1])
            except ValueError:
                await message.answer("El número de muestras debe ser un número.")
                return

    samples_per_topic = max(1, min(samples_per_topic, 5))

    topics = await get_topic_samples(
        telegram_chat_id=telegram_chat_id,
        max_messages=300,
        samples_per_topic=samples_per_topic,
    )

    if not topics:
        await message.answer("No hay muestras de Topics para ese chat.")
        return

    lines = [
        "🧪 Muestras por Topic\n",
        f"Chat: {telegram_chat_id}\n",
        f"Muestras por Topic: {samples_per_topic}\n",
    ]

    for topic in topics[:10]:
        topic_name = await get_topic_name(telegram_chat_id, topic["thread_id"])
        display_name = topic_name or f"Topic {topic['thread_id']}"

        lines.append(
            f"\n{display_name} · ID {topic['thread_id']} · "
            f"{topic['message_count']} muestras recientes"
        )

        for sample in topic["samples"]:
            text_preview = " ".join((sample.text or "").split())
            text_preview = text_preview[:100]

            message_link = build_telegram_message_link(
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=sample.telegram_message_id,
            )

            if message_link:
                lines.append(
                    f"- #{sample.telegram_message_id}: {text_preview}\n"
                    f"  {message_link}"
                )
            else:
                lines.append(
                    f"- #{sample.telegram_message_id}: {text_preview}"
                )

    if len(topics) > 10:
        lines.append(f"\nMostrando 10 de {len(topics)} Topics detectados.")

    await message.answer("\n".join(lines))

@dp.message(Command("topicdetail"), AdminOnly())
async def cmd_topicdetail(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()

    sample_limit = 5

    if message.chat.type == "private":
        if len(parts) < 3:
            await message.answer("Uso correcto: /topicdetail CHAT_ID THREAD_ID [n]")
            return

        try:
            telegram_chat_id = int(parts[1])
            thread_id = int(parts[2])
        except ValueError:
            await message.answer("CHAT_ID y THREAD_ID deben ser números.")
            return

        if len(parts) >= 4:
            try:
                sample_limit = int(parts[3])
            except ValueError:
                await message.answer("El número de muestras debe ser un número.")
                return
    else:
        if len(parts) < 2:
            await message.answer("Uso correcto: /topicdetail THREAD_ID [n]")
            return

        telegram_chat_id = message.chat.id

        try:
            thread_id = int(parts[1])
        except ValueError:
            await message.answer("THREAD_ID debe ser un número.")
            return

        if len(parts) >= 3:
            try:
                sample_limit = int(parts[2])
            except ValueError:
                await message.answer("El número de muestras debe ser un número.")
                return

    sample_limit = max(1, min(sample_limit, 10))

    topic_name = await get_topic_name(
        telegram_chat_id,
        thread_id,
    )

    display_name = topic_name or f"Topic {thread_id}"

    samples = await get_topic_message_samples(
        telegram_chat_id=telegram_chat_id,
        thread_id=thread_id,
        limit=sample_limit,
    )

    if not samples:
        await message.answer("No hay muestras para ese Topic.")
        return

    lines = [
        "🔎 Detalle de Topic\n",
        f"Chat: {telegram_chat_id}",
        f"Topic: {display_name}",
        f"Thread ID: {thread_id}",
        f"Muestras: {len(samples)}\n",
    ]

    for sample in samples:
        text_preview = " ".join((sample.text or "").split())

        if text_preview:
            text_preview = text_preview[:180]
        else:
            content_types = []

            if sample.has_photo:
                content_types.append("foto")

            if sample.has_video:
                content_types.append("vídeo")

            if sample.has_document:
                content_types.append("documento")

            if not content_types:
                content_types.append("mensaje sin texto")

            text_preview = "[" + ", ".join(content_types) + "]"

        message_link = build_telegram_message_link(
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=sample.telegram_message_id,
        )

        if message_link:
            lines.append(
                f"#{sample.telegram_message_id}: {text_preview}\n"
                f"{message_link}\n"
            )
        else:
            lines.append(
                f"#{sample.telegram_message_id}: {text_preview}\n"
            )

    await message.answer("\n".join(lines))

@dp.message(Command("settopic"), AdminOnly())
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

@dp.message(Command("settopicid"), AdminOnly())
async def cmd_settopicid(message: Message):
    if not is_admin_user(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split(maxsplit=3)

    if len(parts) < 4:
        await message.answer(
            "Uso correcto:\n"
            "/settopicid CHAT_ID THREAD_ID Nombre del Topic"
        )
        return

    try:
        telegram_chat_id = int(parts[1])
        thread_id = int(parts[2])
    except ValueError:
        await message.answer("CHAT_ID y THREAD_ID deben ser números.")
        return

    topic_name = parts[3].strip()

    if not topic_name:
        await message.answer("El nombre del Topic no puede estar vacío.")
        return

    await save_topic_name(
        telegram_chat_id=telegram_chat_id,
        thread_id=thread_id,
        name=topic_name,
    )

    await message.answer(
        "✅ Topic guardado en TAIO\n\n"
        f"Chat ID: {telegram_chat_id}\n"
        f"Thread ID: {thread_id}\n"
        f"Nombre: {topic_name}"
    )

async def handle_topic_service_event(message: Message) -> bool:
    thread_id = message.message_thread_id

    if thread_id is None:
        return False

    topic_created = getattr(message, "forum_topic_created", None)
    topic_edited = getattr(message, "forum_topic_edited", None)
    topic_closed = getattr(message, "forum_topic_closed", None)
    topic_reopened = getattr(message, "forum_topic_reopened", None)

    if topic_created:
        topic_name = getattr(topic_created, "name", None)

        await mark_topic_seen(
            telegram_chat_id=message.chat.id,
            thread_id=thread_id,
            name=topic_name,
        )

        return True

    if topic_edited:
        topic_name = getattr(topic_edited, "name", None)

        await mark_topic_seen(
            telegram_chat_id=message.chat.id,
            thread_id=thread_id,
            name=topic_name,
        )

        return True

    if topic_closed:
        await mark_topic_closed(
            telegram_chat_id=message.chat.id,
            thread_id=thread_id,
        )

        return True

    if topic_reopened:
        await mark_topic_reopened(
            telegram_chat_id=message.chat.id,
            thread_id=thread_id,
        )

        return True

    return False


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
    
    if not is_allowed_chat(message.chat.id):
        logging.warning(f"Chat no autorizado ignorado: {message.chat.id}")
        return
    
    if await handle_topic_service_event(message):
        logging.info(
            f"Evento de Topic procesado: chat={message.chat.id}, "
            f"thread={message.message_thread_id}, message={message.message_id}"
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