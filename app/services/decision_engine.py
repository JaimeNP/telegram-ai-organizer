from app.models.decision import BotDecision
from app.models.message import TelegramMessage
from app.moderation.rules import check_message_rules
from app.repositories.topic_repository import get_topic_name
from app.services.duplicate_detector import detect_duplicate, detect_exact_duplicate
from app.services.flood_detector import detect_flood
from app.services.learning_classifier import classify_topic_by_learning
from app.services.link_detector import detect_links
from app.services.topic_classifier import classify_topic
from app.services.topic_keyword_classifier import classify_topic_by_keywords


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

    flood = await detect_flood(message)

    if flood.is_flood:
        return BotDecision(
            action="would_flag_flood",
            reason=(
                f"El usuario ha enviado {flood.message_count} mensajes "
                f"en los últimos {flood.window_seconds} segundos."
            ),
            confidence=0.85,
            simulated=True,
        )

    exact_duplicate = await detect_exact_duplicate(message)

    if exact_duplicate.is_duplicate:
        return BotDecision(
            action="would_delete_exact_duplicate",
            reason=(
                f"Duplicado exacto en General del mismo usuario. "
                f"Mensaje original: {exact_duplicate.original_message_id}."
            ),
            confidence=0.99,
            simulated=True,
        )

    learning_topic = await classify_topic_by_learning(message)

    if learning_topic.should_move:
        topic_name = await get_topic_name(
            telegram_chat_id=message.telegram_chat_id,
            thread_id=learning_topic.target_thread_id,
        )

        topic_display = topic_name or f"Topic {learning_topic.target_thread_id}"
        matched_keywords = ", ".join(learning_topic.matched_keywords or [])

        return BotDecision(
            action="would_move_to_topic",
            reason=(
                f"El mensaje publicado en General se parece a una corrección "
                f"previa de admin hacia {topic_display}: {matched_keywords}."
            ),
            confidence=learning_topic.confidence,
            simulated=True,
        )

    learned_stay_in_general = learning_topic.should_stay_in_general

    if not learned_stay_in_general:
        keyword_topic = classify_topic_by_keywords(message)

        if keyword_topic.should_move:
            topic_name = await get_topic_name(
                telegram_chat_id=message.telegram_chat_id,
                thread_id=keyword_topic.target_thread_id,
            )

            topic_display = topic_name or f"Topic {keyword_topic.target_thread_id}"
            matched_keywords = ", ".join(keyword_topic.matched_keywords or [])

            return BotDecision(
                action="would_move_to_topic",
                reason=(
                    f"El mensaje publicado en General contiene términos asociados a "
                    f"{topic_display}: {matched_keywords}."
                ),
                confidence=keyword_topic.confidence,
                simulated=True,
            )

        topic = await classify_topic(message)

        if topic.should_move:
            topic_name = await get_topic_name(
                telegram_chat_id=message.telegram_chat_id,
                thread_id=topic.target_thread_id,
            )

            topic_display = topic_name or f"Topic {topic.target_thread_id}"

            return BotDecision(
                action="would_move_to_topic",
                reason=(
                    f"El mensaje publicado en General se parece a contenido de "
                    f"{topic_display}. Referencia: mensaje "
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

    links = detect_links(message.text)

    if links.has_links:
        return BotDecision(
            action="would_analyze_link",
            reason=(
                f"El mensaje contiene {len(links.links)} enlace(s). "
                "En una fase posterior TAIO analizará su contenido para sugerir el Topic adecuado."
            ),
            confidence=0.70,
            simulated=True,
        )

    return BotDecision(
        action="allow",
        reason="No se ha detectado ningún problema.",
        confidence=1.0,
        simulated=True,
    )