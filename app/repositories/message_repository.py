from sqlalchemy import desc, select

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


async def get_recent_text_messages(
    telegram_chat_id: int,
    limit: int = 50,
) -> list[StoredMessage]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.text.is_not(None))
            .order_by(desc(StoredMessage.date))
            .limit(limit)
        )

        return list(result.scalars().all())


async def get_recent_topic_text_messages(
    telegram_chat_id: int,
    limit: int = 100,
) -> list[StoredMessage]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.thread_id.is_not(None))
            .where(StoredMessage.text.is_not(None))
            .order_by(desc(StoredMessage.date))
            .limit(limit)
        )

        return list(result.scalars().all())


async def get_recent_user_messages(
    telegram_chat_id: int,
    user_id: int,
    limit: int = 10,
) -> list[StoredMessage]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.user_id == user_id)
            .order_by(desc(StoredMessage.date))
            .limit(limit)
        )

        return list(result.scalars().all())