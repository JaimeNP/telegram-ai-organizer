from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

from app.models.message import TelegramMessage
from app.repositories.learning_repository import get_learning_examples


@dataclass
class LearningTopicResult:
    should_move: bool
    should_stay_in_general: bool
    target_thread_id: int | None = None
    confidence: float = 0.0
    matched_keywords: list[str] | None = None
    reference_message_id: int | None = None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    normalized = text.lower()
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    return " ".join(normalized.split())


def similarity_score(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


async def classify_topic_by_learning(
    message: TelegramMessage,
    threshold: float = 0.72,
) -> LearningTopicResult:
    if message.thread_id is not None:
        return LearningTopicResult(
            should_move=False,
            should_stay_in_general=False,
        )

    current_text = normalize_text(message.text)

    if len(current_text) < 10:
        return LearningTopicResult(
            should_move=False,
            should_stay_in_general=False,
        )

    examples = await get_learning_examples(
        telegram_chat_id=message.telegram_chat_id,
        limit=300,
    )

    best_example = None
    best_score = 0.0

    for example in examples:
        example_text = normalize_text(example.text)

        if len(example_text) < 10:
            continue

        score = similarity_score(current_text, example_text)

        if score > best_score:
            best_score = score
            best_example = example

    if not best_example or best_score < threshold:
        return LearningTopicResult(
            should_move=False,
            should_stay_in_general=False,
        )

    if best_example.label == "allow_general":
        return LearningTopicResult(
            should_move=False,
            should_stay_in_general=True,
            confidence=best_score,
            matched_keywords=[
                f"parecido a mensaje aprobado #{best_example.telegram_message_id}"
            ],
            reference_message_id=best_example.telegram_message_id,
        )

    if best_example.label == "move_to_topic" and best_example.target_thread_id:
        return LearningTopicResult(
            should_move=True,
            should_stay_in_general=False,
            target_thread_id=best_example.target_thread_id,
            confidence=min(0.95, best_score),
            matched_keywords=[
                f"parecido a corrección admin #{best_example.telegram_message_id}"
            ],
            reference_message_id=best_example.telegram_message_id,
        )

    return LearningTopicResult(
        should_move=False,
        should_stay_in_general=False,
    )