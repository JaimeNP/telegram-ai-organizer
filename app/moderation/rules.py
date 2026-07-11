from dataclasses import dataclass


BANNED_WORDS = {
    "gilipollas",
    "imbécil",
    "imbecil",
    "idiota",
    "subnormal",
    "estúpido",
    "estupido",
    "cabrón",
    "cabron",
    "hijo de puta",

}


@dataclass
class ModerationResult:
    violated: bool
    reason: str | None = None
    severity: str = "none"


def is_mostly_uppercase(text: str | None) -> bool:
    if not text:
        return False

    letters = [char for char in text if char.isalpha()]

    if len(letters) < 8:
        return False

    uppercase_letters = [char for char in letters if char.isupper()]

    ratio = len(uppercase_letters) / len(letters)

    return ratio >= 0.8


def contains_banned_word(text: str | None) -> str | None:
    if not text:
        return None

    normalized = text.lower()

    for word in BANNED_WORDS:
        if word in normalized:
            return word

    return None


def check_message_rules(text: str | None) -> ModerationResult:
    banned_word = contains_banned_word(text)

    if banned_word:
        return ModerationResult(
            violated=True,
            reason="El mensaje contiene lenguaje ofensivo.",
            severity="high",
        )

    if is_mostly_uppercase(text):
        return ModerationResult(
            violated=True,
            reason="El mensaje está escrito mayoritariamente en mayúsculas.",
            severity="medium",
        )

    return ModerationResult(violated=False)