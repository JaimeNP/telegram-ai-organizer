from app.models.decision import BotDecision
from app.models.message import TelegramMessage
from app.moderation.rules import check_message_rules
from app.services.duplicate_detector import detect_duplicate
from app.services.topic_classifier import classify_topic


async def decide_for_message(message: TelegramMessage) -> BotDecision:
    moderation = check_message_rules(message.text)

    if moderation.violated:
        confidence = 0.95 if moderation.severity == "high" else 0.85

        return BotDecision(
            action="would_flag_moderation",
            reason=moderation.reason or "Incumple una regla de moderación.",
            confidence=confidence,
            simulated=True,
        )

    topic = await classify_topic(message)

    if topic.should_move:
        return BotDecision(
            action="would_move_to_topic",
            reason=(
                f"El mensaje publicado en General se parece a contenido del Topic "
                f"{topic.target_thread_id}. Referencia: mensaje "
                f"{topic.reference_message_id}."
            ),
            confidence=topic.confidence,
            simulated=True,
        )

    duplicate = await detect_duplicate(message)

    if duplicate.is_duplicate:
        return BotDecision(
            action="would_delete_duplicate",
            reason=(
                f"Mensaje duplicado con similitud "
                f"{duplicate.similarity:.2%} respecto al mensaje "
                f"{duplicate.original_message_id}."
            ),
            confidence=duplicate.similarity,
            simulated=True,
        )

    return BotDecision(
        action="allow",
        reason="No se ha detectado ningún problema.",
        confidence=1.0,
        simulated=True,
    )