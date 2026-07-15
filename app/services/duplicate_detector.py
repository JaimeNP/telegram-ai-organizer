from dataclasses import dataclass
from difflib import SequenceMatcher


from datetime import timedelta

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models.message import TelegramMessage
from app.repositories.message_repository import (
    get_recent_text_messages,
    get_recent_user_messages,
)


@dataclass
class DuplicateResult:
    is_duplicate: bool
    similarity: float = 0.0
    original_message_id: int | None = None
    original_text: str | None = None


URL_PATTERN = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

IGNORED_LINK_HOSTS = {
    "t.me",
    "telegram.me",
    "www.t.me",
    "www.telegram.me",
}


def normalize_url(raw_url: str) -> str | None:
    url = raw_url.strip().rstrip(".,;:!?)»”\"'")

    if url.lower().startswith("www."):
        url = "https://" + url

    try:
        parsed = urlsplit(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()

    if not host or host in IGNORED_LINK_HOSTS:
        return None

    if host.startswith("www."):
        host = host[4:]

    path = parsed.path.rstrip("/")

    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS
    ]

    query = urlencode(sorted(query_items))

    return urlunsplit(
        (
            parsed.scheme.lower() or "https",
            host,
            path,
            query,
            "",
        )
    )


def extract_normalized_urls(text: str) -> set[str]:
    urls: set[str] = set()

    for match in URL_PATTERN.findall(text or ""):
        normalized = normalize_url(match)
        if normalized:
            urls.add(normalized)

    return urls


def text_without_urls(text: str) -> str:
    return " ".join(URL_PATTERN.sub("", text or "").split())

def token_set(text: str) -> set[str]:
    return {
        token
        for token in normalize_text(text).split()
        if len(token) >= 4
    }


def token_overlap_ratio(first_text: str, second_text: str) -> float:
    first_tokens = token_set(first_text)
    second_tokens = token_set(second_text)

    if not first_tokens or not second_tokens:
        return 0.0

    intersection = len(first_tokens.intersection(second_tokens))
    smaller = min(len(first_tokens), len(second_tokens))

    return intersection / smaller


def length_ratio_ok(first_text: str, second_text: str) -> bool:
    first_length = len(normalize_text(first_text))
    second_length = len(normalize_text(second_text))

    if first_length == 0 or second_length == 0:
        return False

    ratio = first_length / second_length

    return 0.75 <= ratio <= 1.35

def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    return " ".join(text.lower().strip().split())


def similarity_score(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


async def detect_duplicate(
    message: TelegramMessage,
    threshold: float = 0.75,
) -> DuplicateResult:
    current_text = normalize_text(message.text)

    if len(current_text) < 10:
        return DuplicateResult(is_duplicate=False)

    recent_messages = await get_recent_text_messages(
        telegram_chat_id=message.telegram_chat_id,
        limit=50,
    )

    for previous in recent_messages:
        if previous.telegram_message_id == message.telegram_message_id:
            continue

        previous_text = normalize_text(previous.text)
        score = similarity_score(current_text, previous_text)

        if score >= threshold:
            return DuplicateResult(
                is_duplicate=True,
                similarity=score,
                original_message_id=previous.telegram_message_id,
                original_text=previous.text,
            )

    return DuplicateResult(is_duplicate=False)

async def detect_exact_duplicate(
    message: TelegramMessage,
    window_seconds: int = 600,
    min_chars: int = 20,
) -> DuplicateResult:
    if message.thread_id is not None:
        return DuplicateResult(is_duplicate=False)

    if message.user_id == 0:
        return DuplicateResult(is_duplicate=False)

    current_text = normalize_text(message.text)

    if len(current_text) < min_chars:
        return DuplicateResult(is_duplicate=False)

    recent_messages = await get_recent_user_messages(
        telegram_chat_id=message.telegram_chat_id,
        user_id=message.user_id,
        limit=20,
    )

    window_start = message.date - timedelta(seconds=window_seconds)

    for previous in recent_messages:
        if previous.telegram_message_id >= message.telegram_message_id:
            continue

        if previous.thread_id != message.thread_id:
            continue

        if previous.date < window_start:
            continue

        previous_text = normalize_text(previous.text)

        if previous_text == current_text:
            return DuplicateResult(
                is_duplicate=True,
                similarity=1.0,
                original_message_id=previous.telegram_message_id,
                original_text=previous.text,
            )

    return DuplicateResult(is_duplicate=False)

async def detect_general_duplicate(
    message: TelegramMessage,
    window_hours: int = 72,
    min_text_chars: int = 80,
    max_own_text_around_link: int = 160,
) -> DuplicateResult:
    if message.thread_id is not None:
        return DuplicateResult(False)

    if message.user_id == 0:
        return DuplicateResult(False)

    reply_to_message_id = getattr(message, "reply_to_message_id", None)
    if reply_to_message_id is not None:
        return DuplicateResult(False)

    current_text = message.text or ""
    current_normalized_text = normalize_text(current_text)
    current_urls = extract_normalized_urls(current_text)
    current_text_without_urls = normalize_text(text_without_urls(current_text))

    if not current_urls and len(current_normalized_text) < min_text_chars:
        return DuplicateResult(False)

    recent_messages = await get_recent_text_messages(
        message.telegram_chat_id,
        limit=300,
    )

    window_start = message.date - timedelta(hours=window_hours)

    for previous in recent_messages:
        if previous.telegram_message_id >= message.telegram_message_id:
            continue

        if previous.thread_id is not None:
            continue

        if previous.date < window_start:
            continue

        previous_text = previous.text or ""

        if current_urls:
            if len(current_text_without_urls) > max_own_text_around_link:
                return DuplicateResult(False)

            previous_urls = extract_normalized_urls(previous_text)

            if current_urls.intersection(previous_urls):
                return DuplicateResult(
                    True,
                    1.0,
                    previous.telegram_message_id,
                    previous.text,
                )

        if len(current_normalized_text) >= min_text_chars:
            previous_normalized_text = normalize_text(previous_text)

            if previous_normalized_text == current_normalized_text:
                return DuplicateResult(
                    True,
                    1.0,
                    previous.telegram_message_id,
                    previous.text,
                )

    return DuplicateResult(False)

async def detect_similar_general_duplicate(
    message: TelegramMessage,
    window_hours: int = 72,
    min_text_chars: int = 160,
    similarity_threshold: float = 0.96,
    token_overlap_threshold: float = 0.88,
) -> DuplicateResult:
    if message.thread_id is not None:
        return DuplicateResult(False)

    if message.user_id == 0:
        return DuplicateResult(False)

    reply_to_message_id = getattr(message, "reply_to_message_id", None)
    if reply_to_message_id is not None:
        return DuplicateResult(False)

    current_text = message.text or ""
    current_normalized_text = normalize_text(current_text)

    if len(current_normalized_text) < min_text_chars:
        return DuplicateResult(False)

    recent_messages = await get_recent_text_messages(
        message.telegram_chat_id,
        limit=300,
    )

    window_start = message.date - timedelta(hours=window_hours)

    for previous in recent_messages:
        if previous.telegram_message_id >= message.telegram_message_id:
            continue

        if previous.thread_id is not None:
            continue

        if previous.date < window_start:
            continue

        previous_text = previous.text or ""
        previous_normalized_text = normalize_text(previous_text)

        if len(previous_normalized_text) < min_text_chars:
            continue

        if not length_ratio_ok(current_text, previous_text):
            continue

        overlap = token_overlap_ratio(current_text, previous_text)

        if overlap < token_overlap_threshold:
            continue

        similarity = SequenceMatcher(
            None,
            current_normalized_text,
            previous_normalized_text,
        ).ratio()

        if similarity >= similarity_threshold:
            return DuplicateResult(
                True,
                similarity,
                previous.telegram_message_id,
                previous.text,
            )

    return DuplicateResult(False)