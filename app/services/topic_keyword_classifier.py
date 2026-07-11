from dataclasses import dataclass
import re
import unicodedata

from app.models.message import TelegramMessage


AIRBUS_CHAT_ID = -1003710195540


AIRBUS_TOPIC_KEYWORDS: dict[int, dict[str, int]] = {
    9482: {
        "teletrabajo": 3,
        "jornada": 2,
        "seleccion de jornada": 4,
        "selección de jornada": 4,
        "vacaciones": 2,
        "conciliacion": 3,
        "conciliación": 3,
        "salario": 2,
        "salario de ingreso": 4,
        "rsi": 3,
        "ipc": 2,
        "dietas": 3,
        "forfait": 3,
        "viajes": 2,
        "etime": 3,
        "pg122": 3,
        "comedor": 3,
        "subida": 2,
        "horas tym": 3,
        "t&m": 3,
    },
    21638: {
        "documento": 2,
        "borrador": 3,
        "pestaña": 3,
        "excel": 3,
        "hoja": 3,
        "redaccion": 3,
        "redacción": 3,
        "comentarios": 2,
        "añadiria": 3,
        "añadiría": 3,
        "eliminaria": 3,
        "eliminaría": 3,
        "texto": 1,
    },
    21630: {
        "comite de huelga": 4,
        "comité de huelga": 4,
        "piquete": 3,
        "piquetes": 3,
        "carpa": 3,
        "puerta sur": 3,
        "san pablo": 2,
        "tablada": 2,
        "illescas": 3,
        "iñlescas": 3,
        "acceso de vehiculos": 4,
        "acceso de vehículos": 4,
    },
    21634: {
        "prensa": 3,
        "periodista": 3,
        "comunicacion": 3,
        "comunicación": 3,
        "bloomberg": 4,
        "eldiario": 4,
        "economista": 3,
        "infodefensa": 4,
        "el español": 4,
        "interlocutor": 3,
        "contacto en la prensa": 4,
    },
    3302: {
        "comunicado oficial": 4,
        "comunicado": 2,
        "sindicato": 2,
        "sindicatos": 2,
        "sipa": 3,
        "ccoo": 2,
        "ugt": 2,
        "cgt": 2,
    },
    9628: {
        "manifestacion": 4,
        "manifestación": 4,
        "manifestaciones": 4,
        "marcha": 4,
        "marchas": 4,
        "ante trabajo": 4,
        "ministerio de trabajo": 4,
        "industria y defensa": 4,
    },
    14577: {
        "avionrevue": 4,
        "voiceofemirates": 4,
        "twitter": 3,
        "x.com": 3,
        "linkedin": 3,
        "redes sociales": 3,
        "aparicion": 3,
        "aparición": 3,
        "noticia": 1,
        "noticias": 1,
        "medios": 3,
    },
    15949: {
        "bloqueados": 3,
        "bloqueado": 3,
        "impacto de la huelga": 4,
        "falta de entregas": 4,
        "entregas de sw": 4,
        "nh90": 4,
    },
    20559: {
        "grupo de trabajo": 4,
        "grupos de trabajo": 4,
        "wg": 2,
        "necesita gente": 4,
        "necesitan gente": 4,
    },
}


@dataclass
class KeywordTopicResult:
    should_move: bool
    target_thread_id: int | None = None
    confidence: float = 0.0
    matched_keywords: list[str] | None = None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    normalized = text.lower()
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    return " ".join(normalized.split())


def keyword_in_text(keyword: str, text: str) -> bool:
    normalized_keyword = normalize_text(keyword)

    if " " in normalized_keyword:
        return normalized_keyword in text

    pattern = rf"\b{re.escape(normalized_keyword)}\b"
    return re.search(pattern, text) is not None


def classify_topic_by_keywords(
    message: TelegramMessage,
) -> KeywordTopicResult:
    if message.telegram_chat_id != AIRBUS_CHAT_ID:
        return KeywordTopicResult(should_move=False)

    if message.thread_id is not None:
        return KeywordTopicResult(should_move=False)

    normalized_text = normalize_text(message.text)

    if len(normalized_text) < 10:
        return KeywordTopicResult(should_move=False)

    best_thread_id = None
    best_score = 0
    best_matches: list[str] = []

    for thread_id, weighted_keywords in AIRBUS_TOPIC_KEYWORDS.items():
        matches = []
        score = 0

        for keyword, weight in weighted_keywords.items():
            if keyword_in_text(keyword, normalized_text):
                matches.append(keyword)
                score += weight

        if score > best_score:
            best_thread_id = thread_id
            best_score = score
            best_matches = matches

    if not best_thread_id or best_score < 3:
        return KeywordTopicResult(should_move=False)

    confidence = min(0.92, 0.62 + (0.08 * best_score))

    return KeywordTopicResult(
        should_move=True,
        target_thread_id=best_thread_id,
        confidence=confidence,
        matched_keywords=sorted(best_matches),
    )