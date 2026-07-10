from sqlalchemy import desc, func, select

from app.database.models import StoredDecision, StoredMessage
from app.database.session import AsyncSessionLocal


async def get_basic_stats() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        messages_result = await session.execute(
            select(func.count()).select_from(StoredMessage)
        )
        decisions_result = await session.execute(
            select(func.count()).select_from(StoredDecision)
        )

        return {
            "messages": messages_result.scalar_one(),
            "decisions": decisions_result.scalar_one(),
        }


async def get_recent_decisions(limit: int = 5) -> list[StoredDecision]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredDecision)
            .order_by(desc(StoredDecision.created_at))
            .limit(limit)
        )

        return list(result.scalars().all())

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