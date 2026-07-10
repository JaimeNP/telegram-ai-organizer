from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models.message import TelegramMessage
from app.repositories.message_repository import get_recent_topic_text_messages


@dataclass
class TopicClassificationResult:
    should_move: bool
    target_thread_id: int | None = None
    confidence: float = 0.0
    reference_message_id: int | None = None
    reference_text: str | None = None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    return " ".join(text.lower().strip().split())


def similarity_score(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


async def classify_topic(
    message: TelegramMessage,
    threshold: float = 0.75,
) -> TopicClassificationResult:
    if message.thread_id is not None:
        return TopicClassificationResult(should_move=False)

    current_text = normalize_text(message.text)

    if len(current_text) < 10:
        return TopicClassificationResult(should_move=False)

    topic_messages = await get_recent_topic_text_messages(
        telegram_chat_id=message.telegram_chat_id,
        limit=100,
    )

    best_score = 0.0
    best_message = None

    for previous in topic_messages:
        previous_text = normalize_text(previous.text)
        score = similarity_score(current_text, previous_text)

        if score > best_score:
            best_score = score
            best_message = previous

    if best_message and best_score >= threshold:
        return TopicClassificationResult(
            should_move=True,
            target_thread_id=best_message.thread_id,
            confidence=best_score,
            reference_message_id=best_message.telegram_message_id,
            reference_text=best_message.text,
        )

    return TopicClassificationResult(should_move=False)