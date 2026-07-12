from datetime import datetime, timezone

from sqlalchemy import func, select

from app.database.models import StoredLearningExample, StoredMessage
from app.database.session import AsyncSessionLocal


async def get_message_by_telegram_id(
    telegram_chat_id: int,
    telegram_message_id: int,
) -> StoredMessage | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.telegram_message_id == telegram_message_id)
        )

        return result.scalar_one_or_none()


async def save_learning_example(
    telegram_chat_id: int,
    telegram_message_id: int,
    source_thread_id: int | None,
    label: str,
    target_thread_id: int | None,
    text: str | None,
    created_by_user_id: int | None,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredLearningExample)
            .where(StoredLearningExample.telegram_chat_id == telegram_chat_id)
            .where(StoredLearningExample.telegram_message_id == telegram_message_id)
        )

        existing = result.scalar_one_or_none()

        if existing:
            existing.source_thread_id = source_thread_id
            existing.label = label
            existing.target_thread_id = target_thread_id
            existing.text = text
            existing.created_by_user_id = created_by_user_id
            existing.created_at = datetime.now(timezone.utc)
        else:
            session.add(
                StoredLearningExample(
                    telegram_chat_id=telegram_chat_id,
                    telegram_message_id=telegram_message_id,
                    source_thread_id=source_thread_id,
                    label=label,
                    target_thread_id=target_thread_id,
                    text=text,
                    created_by_user_id=created_by_user_id,
                    created_at=datetime.now(timezone.utc),
                )
            )

        await session.commit()


async def get_learning_examples(
    telegram_chat_id: int,
    limit: int = 300,
) -> list[StoredLearningExample]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredLearningExample)
            .where(StoredLearningExample.telegram_chat_id == telegram_chat_id)
            .order_by(StoredLearningExample.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())
    
async def get_learning_example_for_message(
    telegram_chat_id: int,
    telegram_message_id: int,
) -> StoredLearningExample | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredLearningExample)
            .where(StoredLearningExample.telegram_chat_id == telegram_chat_id)
            .where(StoredLearningExample.telegram_message_id == telegram_message_id)
        )

        return result.scalar_one_or_none()

async def get_recent_learning_examples(
    telegram_chat_id: int,
    limit: int = 20,
) -> list[StoredLearningExample]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredLearningExample)
            .where(StoredLearningExample.telegram_chat_id == telegram_chat_id)
            .order_by(StoredLearningExample.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())
    
async def get_learning_stats(
    telegram_chat_id: int,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                StoredLearningExample.label,
                StoredLearningExample.target_thread_id,
                func.count(StoredLearningExample.id),
            )
            .where(StoredLearningExample.telegram_chat_id == telegram_chat_id)
            .group_by(
                StoredLearningExample.label,
                StoredLearningExample.target_thread_id,
            )
            .order_by(
                StoredLearningExample.label,
                StoredLearningExample.target_thread_id,
            )
        )

        rows = result.all()

        return [
            {
                "label": row[0],
                "target_thread_id": row[1],
                "count": row[2],
            }
            for row in rows
        ]