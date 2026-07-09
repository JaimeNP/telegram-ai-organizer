from datetime import datetime, timezone

from app.database.models import StoredDecision
from app.database.session import AsyncSessionLocal
from app.models.decision import BotDecision
from app.models.message import TelegramMessage


async def save_decision(
    message: TelegramMessage,
    decision: BotDecision,
) -> None:
    async with AsyncSessionLocal() as session:
        stored = StoredDecision(
            telegram_chat_id=message.telegram_chat_id,
            telegram_message_id=message.telegram_message_id,
            action=decision.action,
            reason=decision.reason,
            confidence=decision.confidence,
            simulated=decision.simulated,
            created_at=datetime.now(timezone.utc),
        )

        session.add(stored)
        await session.commit()