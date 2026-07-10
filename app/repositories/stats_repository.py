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