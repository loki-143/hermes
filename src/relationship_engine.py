from typing import List
from src.models import NormalizedMessage, ContactProfile
from src.style_engine import extract_style_metrics, TELUGU_SLANG_WORDS

FORMAL_WORDS = {
    "sir", "ma'am", "prof", "professor", "thanks", "thank", "regards", "please",
    "submit", "assignment", "office", "meeting", "deadline", "sincerely"
}

FAMILY_WORDS = {
    "amma", "nanna", "akka", "bavagaru", "pinni", "babai", "home", "thinnava"
}

def analyze_relationship_profile(
    contact_id: str,
    display_name: str,
    messages: List[NormalizedMessage]
) -> ContactProfile:
    user_msgs = [m for m in messages if m.is_user]
    style = extract_style_metrics(user_msgs)

    # Classify formality & relationship category
    formal_hits = 0
    family_hits = 0
    total_words = 0

    for msg in user_msgs:
        words = msg.message_text.lower().split()
        total_words += len(words)
        for w in words:
            clean_w = w.strip(".,!?~")
            if clean_w in FORMAL_WORDS:
                formal_hits += 1
            if clean_w in FAMILY_WORDS:
                family_hits += 1

    if total_words > 0:
        formal_ratio = formal_hits / total_words
        family_ratio = family_hits / total_words
    else:
        formal_ratio, family_ratio = 0.0, 0.0

    if formal_ratio > 0.05:
        category = "formal_professional"
        formality_score = min(1.0, round(0.5 + formal_ratio * 5, 2))
    elif family_ratio > 0.03:
        category = "family"
        formality_score = 0.2
    elif style["code_switch_ratio"] > 0.1 or any(w in style["slang_words"] for w in ["ra", "machi", "bava"]):
        category = "close_friend"
        formality_score = 0.1
    else:
        category = "acquaintance"
        formality_score = 0.4

    preferred_greetings = []
    for msg in user_msgs:
        for w in msg.message_text.lower().split():
            clean_w = w.strip(".,!?~")
            if clean_w in TELUGU_SLANG_WORDS or clean_w in FORMAL_WORDS or clean_w in ["hi", "hey", "hello", "sir", "bro"]:
                if clean_w not in preferred_greetings:
                    preferred_greetings.append(clean_w)

    return ContactProfile(
        contact_id=contact_id,
        display_name=display_name,
        relationship_category=category,
        formality_score=formality_score,
        preferred_greetings=preferred_greetings[:3],
        code_switching_rate=style["code_switch_ratio"],
        emoji_frequency=round(sum(style["emoji_dist"].values()) / max(1, len(user_msgs)), 2),
        top_emojis=list(style["emoji_dist"].keys())[:5],
        avg_response_length=style["avg_sentence_len"]
    )
