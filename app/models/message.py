from dataclasses import dataclass
from datetime import datetime


@dataclass
class TelegramMessage:

    telegram_message_id: int
    telegram_chat_id: int

    thread_id: int | None
    thread_name: str

    user_id: int
    username: str | None
    full_name: str

    text: str | None

    has_photo: bool
    has_video: bool
    has_document: bool

    reply_to_message_id: int | None

    date: datetime