from sqlalchemy import select

from app.database.models import StoredTopic
from app.database.session import AsyncSessionLocal


async def save_topic_name(
    telegram_chat_id: int,
    thread_id: int,
    name: str,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        topic = result.scalar_one_or_none()

        if topic:
            topic.name = name
        else:
            topic = StoredTopic(
                telegram_chat_id=telegram_chat_id,
                thread_id=thread_id,
                name=name,
            )
            session.add(topic)

        await session.commit()


async def get_topic_name(
    telegram_chat_id: int,
    thread_id: int | None,
) -> str | None:
    if thread_id is None:
        return "General"

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        topic = result.scalar_one_or_none()

        return topic.name if topic else None