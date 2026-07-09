from dataclasses import dataclass


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


def check_message_rules(text: str | None) -> ModerationResult:
    if is_mostly_uppercase(text):
        return ModerationResult(
            violated=True,
            reason="El mensaje está escrito mayoritariamente en mayúsculas.",
            severity="medium",
        )

    return ModerationResult(violated=False)