from sqlalchemy import func, select

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