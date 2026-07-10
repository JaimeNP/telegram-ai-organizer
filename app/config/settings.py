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


_raw_allowed_chat_ids = os.getenv("ALLOWED_CHAT_IDS", "").strip()

ALLOWED_CHAT_IDS: set[int] = set()

if _raw_allowed_chat_ids:
    ALLOWED_CHAT_IDS = {
        int(chat_id.strip())
        for chat_id in _raw_allowed_chat_ids.split(",")
        if chat_id.strip()
    }


def is_allowed_chat(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS