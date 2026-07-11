from sqlalchemy import and_, desc, func, select
from app.database.models import StoredDecision, StoredMessage
from app.database.session import AsyncSessionLocal


async def get_basic_stats(
    telegram_chat_id: int | None = None,
) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        messages_query = select(func.count()).select_from(StoredMessage)
        decisions_query = select(func.count()).select_from(StoredDecision)

        if telegram_chat_id is not None:
            messages_query = messages_query.where(
                StoredMessage.telegram_chat_id == telegram_chat_id
            )
            decisions_query = decisions_query.where(
                StoredDecision.telegram_chat_id == telegram_chat_id
            )

        messages_result = await session.execute(messages_query)
        decisions_result = await session.execute(decisions_query)

        return {
            "messages": messages_result.scalar_one(),
            "decisions": decisions_result.scalar_one(),
        }


async def get_recent_decisions_with_messages(
    limit: int = 5,
    telegram_chat_id: int | None = None,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        query = (
            select(StoredDecision, StoredMessage)
            .outerjoin(
                StoredMessage,
                and_(
                    StoredDecision.telegram_chat_id == StoredMessage.telegram_chat_id,
                    StoredDecision.telegram_message_id == StoredMessage.telegram_message_id,
                ),
            )
            .order_by(desc(StoredDecision.created_at))
            .limit(limit)
        )

        if telegram_chat_id is not None:
            query = query.where(StoredDecision.telegram_chat_id == telegram_chat_id)

        result = await session.execute(query)

        rows = result.all()

        return [
            {
                "decision": row[0],
                "message": row[1],
            }
            for row in rows
        ]
async def get_topic_stats(telegram_chat_id: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                StoredMessage.thread_id,
                func.count(StoredMessage.id),
                func.max(StoredMessage.date),
            )
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.thread_id.is_not(None))
            .group_by(StoredMessage.thread_id)
            .order_by(StoredMessage.thread_id)
        )

        rows = result.all()

        return [
            {
                "thread_id": row[0],
                "messages": row[1],
                "last_message_at": row[2],
            }
            for row in rows
        ]
    
async def get_recent_decisions_with_messages(
    limit: int = 5,
    telegram_chat_id: int | None = None,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        query = (
            select(StoredDecision, StoredMessage)
            .outerjoin(
                StoredMessage,
                and_(
                    StoredDecision.telegram_chat_id == StoredMessage.telegram_chat_id,
                    StoredDecision.telegram_message_id == StoredMessage.telegram_message_id,
                ),
            )
            .order_by(desc(StoredDecision.created_at))
            .limit(limit)
        )

        if telegram_chat_id is not None:
            query = query.where(StoredDecision.telegram_chat_id == telegram_chat_id)

        result = await session.execute(query)

        rows = result.all()

        return [
            {
                "decision": row[0],
                "message": row[1],
            }
            for row in rows
        ]

async def get_decision_action_stats(
    telegram_chat_id: int | None = None,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        query = (
            select(
                StoredDecision.action,
                func.count(StoredDecision.id),
            )
            .group_by(StoredDecision.action)
            .order_by(StoredDecision.action)
        )

        if telegram_chat_id is not None:
            query = query.where(StoredDecision.telegram_chat_id == telegram_chat_id)

        result = await session.execute(query)

        rows = result.all()

        return [
            {
                "action": row[0],
                "count": row[1],
            }
            for row in rows
        ]
    

async def get_topic_samples(
    telegram_chat_id: int,
    max_messages: int = 300,
    samples_per_topic: int = 2,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.thread_id.is_not(None))
            .where(StoredMessage.text.is_not(None))
            .order_by(desc(StoredMessage.date))
            .limit(max_messages)
        )

        messages = list(result.scalars().all())

    grouped: dict[int, list[StoredMessage]] = {}

    for message in messages:
        if message.thread_id is None:
            continue

        grouped.setdefault(message.thread_id, []).append(message)

    topics = []

    for thread_id, topic_messages in grouped.items():
        topics.append(
            {
                "thread_id": thread_id,
                "message_count": len(topic_messages),
                "samples": topic_messages[:samples_per_topic],
            }
        )

    return sorted(
        topics,
        key=lambda topic: topic["message_count"],
        reverse=True,
    )

async def get_topic_message_samples(
    telegram_chat_id: int,
    thread_id: int,
    limit: int = 10,
) -> list[StoredMessage]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredMessage)
            .where(StoredMessage.telegram_chat_id == telegram_chat_id)
            .where(StoredMessage.thread_id == thread_id)
            .where(StoredMessage.text.is_not(None))
            .order_by(desc(StoredMessage.date))
            .limit(limit)
        )

        return list(result.scalars().all())