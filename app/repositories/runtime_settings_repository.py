from datetime import datetime, timezone

from sqlalchemy import select

from app.database.models import StoredRuntimeSetting
from app.database.session import AsyncSessionLocal


REAL_ACTIONS_PAUSED_KEY = "real_actions_paused"


async def set_runtime_setting(
    key: str,
    value: str,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredRuntimeSetting)
            .where(StoredRuntimeSetting.key == key)
        )

        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                StoredRuntimeSetting(
                    key=key,
                    value=value,
                    updated_at=datetime.now(timezone.utc),
                )
            )

        await session.commit()


async def get_runtime_setting(
    key: str,
    default: str = "",
) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoredRuntimeSetting)
            .where(StoredRuntimeSetting.key == key)
        )

        setting = result.scalar_one_or_none()

        return setting.value if setting else default


async def set_real_actions_paused(paused: bool) -> None:
    await set_runtime_setting(
        REAL_ACTIONS_PAUSED_KEY,
        "true" if paused else "false",
    )


async def are_real_actions_paused() -> bool:
    value = await get_runtime_setting(
        REAL_ACTIONS_PAUSED_KEY,
        default="false",
    )

    return value.lower() in {"1", "true", "yes", "on"}