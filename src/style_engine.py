import re
from collections import Counter
from typing import List, Dict, Any
from src.models import NormalizedMessage

TELUGU_SLANG_WORDS = {
    "ra", "machi", "bro", "bava", "mama", "cheppandi", "enti", "akkada", "ikkada",
    "em", "ela", "undhi", "ayyo", "alage", "sare", "le", "ledhu", "kadha", "chudu", "avuna"
}

EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]"
)

def extract_style_metrics(user_messages: List[NormalizedMessage]) -> Dict[str, Any]:
    if not user_messages:
        return {
            "vocab_freq": {},
            "slang_words": {},
            "code_switch_ratio": 0.0,
            "avg_sentence_len": 0.0,
            "emoji_dist": {},
            "punctuation_style": {}
        }

    total_words = 0
    telugu_word_count = 0
    word_counter = Counter()
    slang_counter = Counter()
    emoji_counter = Counter()
    sentence_lengths = []
    punct_counter = Counter()

    for msg in user_messages:
        text = msg.message_text.strip()
        if not text:
            continue
        
        # Extract emojis
        emojis = EMOJI_PATTERN.findall(text)
        emoji_counter.update(emojis)

        # Remove emojis for word tokenization
        clean_text = EMOJI_PATTERN.sub("", text).lower()
        words = re.findall(r"\b[a-z0-9'-]+\b", clean_text)
        
        total_words += len(words)
        sentence_lengths.append(len(words))
        
        for w in words:
            word_counter[w] += 1
            if w in TELUGU_SLANG_WORDS:
                telugu_word_count += 1
                slang_counter[w] += 1
        
        # Punctuation tracking
        for char in text:
            if char in "!?.~":
                punct_counter[char] += 1

    code_switch_ratio = round(telugu_word_count / total_words, 4) if total_words > 0 else 0.0
    avg_sentence_len = round(sum(sentence_lengths) / len(sentence_lengths), 2) if sentence_lengths else 0.0

    return {
        "vocab_freq": dict(word_counter.most_common(50)),
        "slang_words": dict(slang_counter.most_common(20)),
        "code_switch_ratio": code_switch_ratio,
        "avg_sentence_len": avg_sentence_len,
        "emoji_dist": dict(emoji_counter.most_common(20)),
        "punctuation_style": dict(punct_counter)
    }
