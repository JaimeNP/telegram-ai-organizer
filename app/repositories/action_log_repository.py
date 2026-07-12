from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.database.models import StoredActionLog
from app.database.session import AsyncSessionLocal


async def save_action_log(
    telegram_chat_id: int,
    telegram_message_id: int,
    action: str,
    status: str,
    detail: str,
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            StoredActionLog(
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=telegram_message_id,
                action=action,
                status=status,
                detail=detail,
                created_at=datetime.now(timezone.utc),
            )
        )

        await session.commit()


async def get_recent_action_logs(
    telegram_chat_id: int | None = None,
    limit: int = 20,
) -> list[StoredActionLog]:
    async with AsyncSessionLocal() as session:
        query = (
            select(StoredActionLog)
            .order_by(desc(StoredActionLog.created_at))
            .limit(limit)
        )

        if telegram_chat_id is not None:
            query = query.where(
                StoredActionLog.telegram_chat_id == telegram_chat_id
            )

        result = await session.execute(query)

        return list(result.scalars().all())