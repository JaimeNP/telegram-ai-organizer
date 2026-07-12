import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN no encontrado en el archivo .env")


SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ACTION_MODE = os.getenv("ACTION_MODE", "listen").lower()

if ACTION_MODE not in {"listen", "simulate", "auto"}:
    raise RuntimeError("ACTION_MODE debe ser listen, simulate o auto")


ENABLE_DELETES = os.getenv("ENABLE_DELETES", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ENABLE_REPOSTS = os.getenv("ENABLE_REPOSTS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ENABLE_PRIVATE_NOTICES = os.getenv("ENABLE_PRIVATE_NOTICES", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ENABLE_GROUP_NOTICES = os.getenv("ENABLE_GROUP_NOTICES", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

AUTO_DELETE_GROUP_NOTICES_SECONDS = int(
    os.getenv("AUTO_DELETE_GROUP_NOTICES_SECONDS", "20")
)

_raw_allowed_chat_ids = os.getenv("ALLOWED_CHAT_IDS", "").strip()

ALLOWED_CHAT_IDS: set[int] = set()

if _raw_allowed_chat_ids:
    ALLOWED_CHAT_IDS = {
        int(chat_id.strip())
        for chat_id in _raw_allowed_chat_ids.split(",")
        if chat_id.strip()
    }


_raw_admin_user_ids = os.getenv("ADMIN_USER_IDS", "").strip()

ADMIN_USER_IDS: set[int] = set()

if _raw_admin_user_ids:
    ADMIN_USER_IDS = {
        int(user_id.strip())
        for user_id in _raw_admin_user_ids.split(",")
        if user_id.strip()
    }


def is_allowed_chat(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS


def is_admin_user(user_id: int | None) -> bool:
    if user_id is None:
        return False

    return user_id in ADMIN_USER_IDS

_raw_active_delete_chat_ids = os.getenv("ACTIVE_DELETE_CHAT_IDS", "").strip()

ACTIVE_DELETE_CHAT_IDS: set[int] = set()

if _raw_active_delete_chat_ids:
    ACTIVE_DELETE_CHAT_IDS = {
        int(chat_id.strip())
        for chat_id in _raw_active_delete_chat_ids.split(",")
        if chat_id.strip()
    }


def is_active_delete_chat(chat_id: int) -> bool:
    return chat_id in ACTIVE_DELETE_CHAT_IDS