import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.repositories.action_log_repository import save_action_log

from app.config.settings import (
    ACTION_MODE,
    ENABLE_DELETES,
    ENABLE_PRIVATE_NOTICES,
    ENABLE_REPOSTS,
    is_active_delete_chat,
)
from app.models.decision import BotDecision
from app.models.message import TelegramMessage


async def execute_decision(
    bot: Bot,
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
        if decision.action == "would_delete_exact_duplicate":
            if not ENABLE_DELETES:
                logging.warning("Borrado bloqueado por ENABLE_DELETES=false")
                return

            if not is_active_delete_chat(message.telegram_chat_id):
                logging.warning(
                    "Borrado bloqueado: chat no incluido en ACTIVE_DELETE_CHAT_IDS"
                )
                return

            try:
                await bot.delete_message(
                    chat_id=message.telegram_chat_id,
                    message_id=message.telegram_message_id,
                )

                logging.warning(
                    "Mensaje duplicado exacto eliminado: "
                    f"chat={message.telegram_chat_id}, "
                    f"message={message.telegram_message_id}"
                )

                await save_action_log(
                    telegram_chat_id=message.telegram_chat_id,
                    telegram_message_id=message.telegram_message_id,
                    action=decision.action,
                    status="executed",
                    detail="Duplicado exacto eliminado automáticamente.",
                )

                if ENABLE_PRIVATE_NOTICES and message.user_id:
                    try:
                        await bot.send_message(
                            chat_id=message.user_id,
                            text=(
                                "TAIO ha eliminado un mensaje duplicado exacto "
                                "que acababas de enviar en General.\n\n"
                                "No es una sanción; solo ayuda a mantener limpio el grupo."
                            ),
                        )
                    except TelegramAPIError:
                        logging.warning(
                            "No se pudo enviar aviso privado al usuario "
                            f"{message.user_id}"
                        )

            except TelegramAPIError as error:
                logging.exception(
                    "No se pudo borrar el duplicado exacto. "
                    "Comprueba que TAIO tenga permiso para eliminar mensajes."
                )

                await save_action_log(
                    telegram_chat_id=message.telegram_chat_id,
                    telegram_message_id=message.telegram_message_id,
                    action=decision.action,
                    status="failed",
                    detail=f"No se pudo borrar el mensaje: {error}",
                )
            return

        if decision.action == "would_delete_duplicate":
            logging.warning(
                "Duplicado no exacto detectado, pero el borrado automático está bloqueado."
            )
            return

        if decision.action.startswith("would_move") and not ENABLE_REPOSTS:
            logging.warning("Movimiento bloqueado por configuración ENABLE_REPOSTS=false")
            return

        if not ENABLE_PRIVATE_NOTICES:
            logging.warning(
                "Avisos privados bloqueados por configuración ENABLE_PRIVATE_NOTICES=false"
            )

        logging.warning(
            "Modo auto activo, pero esta acción no tiene ejecución real implementada: "
            f"{decision.action}"
        )