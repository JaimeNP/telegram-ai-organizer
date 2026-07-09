from app.database.models import StoredMessage
from app.database.session import AsyncSessionLocal
from app.models.message import TelegramMessage


async def save_message(message: TelegramMessage) -> None:
    async with AsyncSessionLocal() as session:
        stored = StoredMessage(
            telegram_message_id=message.telegram_message_id,
            telegram_chat_id=message.telegram_chat_id,
            thread_id=message.thread_id,
            thread_name=message.thread_name,
            user_id=message.user_id,
            username=message.username,
            full_name=message.full_name,
            text=message.text,
            has_photo=message.has_photo,
            has_video=message.has_video,
            has_document=message.has_document,
            reply_to_message_id=message.reply_to_message_id,
            date=message.date,
        )

        session.add(stored)
        await session.commit()