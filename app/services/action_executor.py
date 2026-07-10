import logging

from app.config.settings import (
    ACTION_MODE,
    ENABLE_DELETES,
    ENABLE_PRIVATE_NOTICES,
    ENABLE_REPOSTS,
)
from app.models.decision import BotDecision
from app.models.message import TelegramMessage


async def execute_decision(
    message: TelegramMessage,
    decision: BotDecision,
) -> None:
    if ACTION_MODE == "listen":
        logging.warning(
            "Modo escucha activo: no se ejecuta ninguna acción real. "
            f"Mensaje={message.telegram_message_id}, acción simulada={decision.action}"
        )
        return

    if ACTION_MODE == "simulate":
        logging.warning(
            "Modo simulación activo: decisión registrada, sin acción real. "
            f"Mensaje={message.telegram_message_id}, acción simulada={decision.action}"
        )
        return

    if ACTION_MODE == "auto":
        if decision.action == "would_delete_duplicate" and not ENABLE_DELETES:
            logging.warning("Borrado bloqueado por configuración ENABLE_DELETES=false")
            return

        if decision.action.startswith("would_move") and not ENABLE_REPOSTS:
            logging.warning("Movimiento bloqueado por configuración ENABLE_REPOSTS=false")
            return

        if not ENABLE_PRIVATE_NOTICES:
            logging.warning("Avisos privados bloqueados por configuración ENABLE_PRIVATE_NOTICES=false")

        logging.warning(
            "Modo auto activo, pero todavía no hay acciones reales implementadas."
        )