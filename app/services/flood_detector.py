from dataclasses import dataclass
from datetime import timedelta

from app.models.message import TelegramMessage
from app.repositories.message_repository import get_recent_user_messages


@dataclass
class FloodDetectionResult:
    is_flood: bool
    message_count: int = 0
    window_seconds: int = 60


async def detect_flood(
    message: TelegramMessage,
    max_messages: int = 5,
    window_seconds: int = 60,
) -> FloodDetectionResult:
    recent_messages = await get_recent_user_messages(
        telegram_chat_id=message.telegram_chat_id,
        user_id=message.user_id,
        limit=max_messages,
    )

    if not recent_messages:
        return FloodDetectionResult(is_flood=False)

    window_start = message.date - timedelta(seconds=window_seconds)

    messages_in_window = [
        recent
        for recent in recent_messages
        if recent.date >= window_start
    ]

    count = len(messages_in_window)

    return FloodDetectionResult(
        is_flood=count >= max_messages,
        message_count=count,
        window_seconds=window_seconds,
    )