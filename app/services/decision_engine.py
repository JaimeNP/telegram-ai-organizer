from app.models.decision import BotDecision
from app.models.message import TelegramMessage
from app.moderation.rules import check_message_rules
from app.services.duplicate_detector import detect_duplicate


async def decide_for_message(message: TelegramMessage) -> BotDecision:
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

    moderation = check_message_rules(message.text)

    if moderation.violated:
        confidence = 0.95 if moderation.severity == "high" else 0.85

        return BotDecision(
            action="would_flag_moderation",
            reason=moderation.reason or "Incumple una regla de moderación.",
            confidence=confidence,
            simulated=True,
        )

    return BotDecision(
        action="allow",
        reason="No se ha detectado ningún problema.",
        confidence=1.0,
        simulated=True,
    )