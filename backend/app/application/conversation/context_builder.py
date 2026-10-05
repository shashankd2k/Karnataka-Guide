"""
Bounded conversation context builder and follow-up query resolver.

Resolves referential pronouns and follow-up questions into self-contained
retrieval queries using the bounded conversation history, while keeping the
original user message unmodified for database persistence.
"""

import re
from typing import List, Optional
from app.infrastructure.db.models.chat import ChatMessage, SenderType

# Pronouns and referential cues in English and Kannada
ENGLISH_REFERENTIAL_REGEX = re.compile(
    r"\b(it|its|this|that|these|those|they|them|there|he|she|here)\b",
    re.IGNORECASE,
)
KANNADA_REFERENTIAL_REGEX = re.compile(
    r"(\b|\s|^)(ಅದು|ಇದು|ಅಲ್ಲಿ|ಇಲ್ಲಿ|ಅವರು|ಅದರ|ಇದರ|ಅದನ್ನು|ಇದನ್ನು)(\b|\s|$)"
)

# Common short follow-up patterns
FOLLOW_UP_PATTERNS = [
    re.compile(r"^(when|who|why|how|what)\s+(was|were|did|is|are)\s+(it|this|that|there)\b", re.IGNORECASE),
    re.compile(r"^(tell me more|more details|what about|how about|explain more)\b", re.IGNORECASE),
    re.compile(r"^(ಯಾವಾಗ|ಯಾರು|ಏಕೆ|ಹೇಗೆ|ಎಲ್ಲಿ)\s*(ಕಟ್ಟಲಾಯಿತು|ನಿರ್ಮಿಸಲಾಯಿತು|ಆಯಿತು|ಇದೆ)?\b"),
]

# Known Karnataka heritage entities and architectural keywords for subject extraction (sorted by length descending)
KNOWN_HERITAGE_ENTITIES = sorted([
    "Belur Chennakeshava Temple",
    "Chennakeshava Temple",
    "Halebidu Hoysaleswara Temple",
    "Hoysaleswara Temple",
    "Badami Cave 1",
    "Badami Cave 2",
    "Badami Cave 3",
    "Badami Cave 4",
    "Badami Caves",
    "Aihole Durga Temple",
    "Durga Temple",
    "Lad Khan Temple",
    "Ravana Phadi Cave",
    "Meguti Hill Jain Temple",
    "Aihole Inscription",
    "Pattadakal Virupaksha Temple",
    "Virupaksha Temple at Pattadakal",
    "Virupaksha Temple at Hampi",
    "Virupaksha Temple",
    "Mallikarjuna Temple",
    "Sangameshwara Temple",
    "Papanatha Temple",
    "Jain Narayana Temple",
    "Vijaya Vittala Temple",
    "Stone Chariot",
    "Lotus Mahal",
    "Elephant Stables",
    "Bhutanatha Temple",
    "Hampi Vijayanagara",
    "Vijayanagara Empire",
    "Pattadakal",
    "Halebidu",
    "Badami",
    "Aihole",
    "Hampi",
    "Belur",
    "Vatapi",
    "Talakadu",
    "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ",
    "ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ",
    "ಹಳೆಬೀಡು ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯ",
    "ಬಾದಾಮಿ ಗುಹೆಗಳು",
    "ಐಹೊಳೆ ದುರ್ಗಾ ದೇವಾಲಯ",
    "ಪಟ್ಟದಕಲ್ಲು ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯ",
    "ಹಂಪಿ ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯ",
    "ಪಟ್ಟದಕಲ್ಲು",
    "ಹಳೆಬೀಡು",
    "ಬಾದಾಮಿ",
    "ಐಹೊಳೆ",
    "ಹಂಪಿ",
    "ಬೇಲೂರು",
], key=len, reverse=True)


def extract_primary_subject(history_messages: List[ChatMessage]) -> Optional[str]:
    """
    Extract the most recent primary heritage subject/entity from recent conversation turns.
    Preserves both specific monuments and overarching heritage site context.
    Prioritizes USER messages to capture tourist intent accurately.
    """
    if not history_messages:
        return None

    OVERARCHING_SITES = [
        "Belur", "Halebidu", "Badami", "Aihole", "Pattadakal", "Hampi", "Talakadu",
        "ಬೇಲೂರು", "ಹಳೆಬೀಡು", "ಬಾದಾಮಿ", "ಐಹೊಳೆ", "ಪಟ್ಟದಕಲ್ಲು", "ಹಂಪಿ"
    ]
    detected_site = None
    detected_monument = None

    # Search in reverse (most recent first), prioritize USER messages
    for msg in reversed(history_messages):
        if msg.sender_type == SenderType.USER:
            text = msg.message_text.strip()
            for entity in KNOWN_HERITAGE_ENTITIES:
                if re.search(r"\b" + re.escape(entity) + r"\b", text, re.IGNORECASE):
                    if entity in OVERARCHING_SITES and not detected_site:
                        detected_site = entity
                    elif entity not in OVERARCHING_SITES and not detected_monument:
                        detected_monument = entity
            if detected_monument and detected_site:
                break

    # Fallback to assistant turns if no subject found
    if not detected_monument and not detected_site:
        for msg in reversed(history_messages):
            text = msg.message_text.strip()
            for entity in KNOWN_HERITAGE_ENTITIES:
                if re.search(r"\b" + re.escape(entity) + r"\b", text, re.IGNORECASE):
                    if entity in OVERARCHING_SITES and not detected_site:
                        detected_site = entity
                    elif entity not in OVERARCHING_SITES and not detected_monument:
                        detected_monument = entity
            if detected_monument and detected_site:
                break

    if detected_monument and detected_site and detected_site.lower() not in detected_monument.lower():
        return f"{detected_site} {detected_monument}"

    return detected_monument or detected_site


def is_follow_up_query(query_text: str) -> bool:
    """
    Determine if a query is a follow-up or referential query requiring previous context.
    """
    cleaned = query_text.strip().rstrip("?").strip()
    words = cleaned.split()

    # Short interrogative words ("Why", "When", "Who", "How", "Why was it built")
    if len(words) <= 3 and not re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", cleaned):
        if any(w.lower() in ("why", "when", "who", "how", "what", "where", "ಯಾವಾಗ", "ಯಾರು", "ಏಕೆ", "ಹೇಗೆ") for w in words):
            return True

    # Pronoun / referential checks
    if ENGLISH_REFERENTIAL_REGEX.search(cleaned):
        return True
    if KANNADA_REFERENTIAL_REGEX.search(cleaned):
        return True

    for p in FOLLOW_UP_PATTERNS:
        if p.search(cleaned):
            return True

    return False


def resolve_follow_up_query(
    current_query: str,
    history_messages: List[ChatMessage],
) -> str:
    """
    Resolve a follow-up user query into a self-contained search query for Phase 7 retrieval.

    Args:
        current_query: The incoming tourist query string.
        history_messages: Chronological list of recent ChatMessage objects for this session.

    Returns:
        A resolved search query containing relevant subject context, or current_query unchanged.
    """
    cleaned_query = current_query.strip()
    if not history_messages:
        return cleaned_query

    if not is_follow_up_query(cleaned_query):
        return cleaned_query

    subject = extract_primary_subject(history_messages)
    if not subject:
        return cleaned_query

    # If already contains the subject, do not duplicate
    if subject.lower() in cleaned_query.lower():
        return cleaned_query

    # Check if we can substitute pronoun directly
    # e.g., "When was it built?" -> "When was Belur Chennakeshava Temple built?"
    if re.search(r"\b(it|this|that)\b", cleaned_query, re.IGNORECASE):
        resolved = re.sub(
            r"\b(it|this|that)\b",
            subject,
            cleaned_query,
            count=1,
            flags=re.IGNORECASE,
        )
        return resolved

    # Kannada pronoun substitution: "ಅದನ್ನು ಯಾರು ಕಟ್ಟಿದರು?" -> "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿದರು?"
    if re.search(r"(\b|^)(ಅದು|ಇದು|ಅದನ್ನು|ಇದನ್ನು)(\b|$)", cleaned_query):
        resolved = re.sub(
            r"(\b|^)(ಅದು|ಇದು|ಅದನ್ನು|ಇದನ್ನು)(\b|$)",
            f" {subject} ",
            cleaned_query,
            count=1,
        )
        return re.sub(r"\s+", " ", resolved).strip()

    # General append: "What architectural style does it use?" / "Tell me more about sculptures"
    # -> "What architectural style does Belur Chennakeshava Temple use?" or "Tell me more about sculptures in Belur Chennakeshava Temple"
    return f"{cleaned_query} ({subject})"
