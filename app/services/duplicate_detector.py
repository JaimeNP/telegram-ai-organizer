from dataclasses import dataclass
from difflib import SequenceMatcher

from datetime import timedelta

from app.models.message import TelegramMessage
from app.repositories.message_repository import (
    get_recent_text_messages,
    get_recent_user_messages,
)


@dataclass
class DuplicateResult:
    is_duplicate: bool
    similarity: float = 0.0
    original_message_id: int | None = None
    original_text: str | None = None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    return " ".join(text.lower().strip().split())


def similarity_score(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


async def detect_duplicate(
    message: TelegramMessage,
    threshold: float = 0.75,
) -> DuplicateResult:
    current_text = normalize_text(message.text)

    if len(current_text) < 10:
        return DuplicateResult(is_duplicate=False)

    recent_messages = await get_recent_text_messages(
        telegram_chat_id=message.telegram_chat_id,
        limit=50,
    )

    for previous in recent_messages:
        if previous.telegram_message_id == message.telegram_message_id:
            continue

        previous_text = normalize_text(previous.text)
        score = similarity_score(current_text, previous_text)

        if score >= threshold:
            return DuplicateResult(
                is_duplicate=True,
                similarity=score,
                original_message_id=previous.telegram_message_id,
                original_text=previous.text,
            )

    return DuplicateResult(is_duplicate=False)

async def detect_exact_duplicate(
    message: TelegramMessage,
    window_seconds: int = 600,
    min_chars: int = 20,
) -> DuplicateResult:
    if message.thread_id is not None:
        return DuplicateResult(is_duplicate=False)

    if message.user_id == 0:
        return DuplicateResult(is_duplicate=False)

    current_text = normalize_text(message.text)

    if len(current_text) < min_chars:
        return DuplicateResult(is_duplicate=False)

    recent_messages = await get_recent_user_messages(
        telegram_chat_id=message.telegram_chat_id,
        user_id=message.user_id,
        limit=20,
    )

    window_start = message.date - timedelta(seconds=window_seconds)

    for previous in recent_messages:
        if previous.telegram_message_id >= message.telegram_message_id:
            continue

        if previous.thread_id != message.thread_id:
            continue

        if previous.date < window_start:
            continue

        previous_text = normalize_text(previous.text)

        if previous_text == current_text:
            return DuplicateResult(
                is_duplicate=True,
                similarity=1.0,
                original_message_id=previous.telegram_message_id,
                original_text=previous.text,
            )

    return DuplicateResult(is_duplicate=False)