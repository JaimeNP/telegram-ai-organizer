from sqlalchemy import text

from app.database.models import Base
from app.database.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(
            text(
                "ALTER TABLE topics "
                "ADD COLUMN IF NOT EXISTS is_closed BOOLEAN NOT NULL DEFAULT false"
            )
        )

        await conn.execute(
            text(
                "ALTER TABLE topics "
                "ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false"
            )
        )

        await conn.execute(
            text(
                "ALTER TABLE topics "
                "ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE"
            )
        )