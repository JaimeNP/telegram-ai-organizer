from datetime import datetime, timezone

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

        topic = result.scalars().first()

        if topic:
            topic.name = name
            topic.is_deleted = False
            topic.last_seen_at = datetime.now(timezone.utc)
        else:
            topic = StoredTopic(
                telegram_chat_id=telegram_chat_id,
                thread_id=thread_id,
                name=name,
                is_closed=False,
                is_deleted=False,
                last_seen_at=datetime.now(timezone.utc),
            )
            session.add(topic)

        await session.commit()


async def mark_topic_seen(
    telegram_chat_id: int,
    thread_id: int,
    name: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        topic = result.scalars().first()

        if topic:
            if name:
                topic.name = name

            topic.is_deleted = False
            topic.last_seen_at = datetime.now(timezone.utc)
        else:
            topic = StoredTopic(
                telegram_chat_id=telegram_chat_id,
                thread_id=thread_id,
                name=name or f"Topic {thread_id}",
                is_closed=False,
                is_deleted=False,
                last_seen_at=datetime.now(timezone.utc),
            )
            session.add(topic)

        await session.commit()


async def mark_topic_closed(
    telegram_chat_id: int,
    thread_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        topic = result.scalars().first()

        if topic:
            topic.is_closed = True
            topic.last_seen_at = datetime.now(timezone.utc)
        else:
            session.add(
                StoredTopic(
                    telegram_chat_id=telegram_chat_id,
                    thread_id=thread_id,
                    name=f"Topic {thread_id}",
                    is_closed=True,
                    is_deleted=False,
                    last_seen_at=datetime.now(timezone.utc),
                )
            )

        await session.commit()


async def mark_topic_reopened(
    telegram_chat_id: int,
    thread_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        topic = result.scalars().first()

        if topic:
            topic.is_closed = False
            topic.is_deleted = False
            topic.last_seen_at = datetime.now(timezone.utc)
        else:
            session.add(
                StoredTopic(
                    telegram_chat_id=telegram_chat_id,
                    thread_id=thread_id,
                    name=f"Topic {thread_id}",
                    is_closed=False,
                    is_deleted=False,
                    last_seen_at=datetime.now(timezone.utc),
                )
            )

        await session.commit()


async def get_topic_info(
    telegram_chat_id: int,
    thread_id: int | None,
) -> StoredTopic | None:
    if thread_id is None:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.thread_id == thread_id)
        )

        return result.scalars().first()


async def get_topic_name(
    telegram_chat_id: int,
    thread_id: int | None,
) -> str | None:
    if thread_id is None:
        return "General"

    topic = await get_topic_info(
        telegram_chat_id=telegram_chat_id,
        thread_id=thread_id,
    )

    return topic.name if topic else None

async def get_active_topics(
    telegram_chat_id: int,
) -> list[StoredTopic]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredTopic)
            .where(StoredTopic.telegram_chat_id == telegram_chat_id)
            .where(StoredTopic.is_closed.is_(False))
            .where(StoredTopic.is_deleted.is_(False))
            .order_by(StoredTopic.name)
        )

        topics = list(result.scalars().all())

    unique_topics: dict[int, StoredTopic] = {}

    for topic in topics:
        if topic.thread_id not in unique_topics:
            unique_topics[topic.thread_id] = topic

    return sorted(
        unique_topics.values(),
        key=lambda topic: topic.name,
    )