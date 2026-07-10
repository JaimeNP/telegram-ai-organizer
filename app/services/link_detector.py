import re
from dataclasses import dataclass


URL_PATTERN = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE,
)


@dataclass
class LinkDetectionResult:
    has_links: bool
    links: list[str]


def detect_links(text: str | None) -> LinkDetectionResult:
    if not text:
        return LinkDetectionResult(has_links=False, links=[])

    links = URL_PATTERN.findall(text)

    return LinkDetectionResult(
        has_links=bool(links),
        links=links,
    )