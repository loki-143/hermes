import pytest
from src.ingestion import parse_whatsapp_chat
from src.style_engine import extract_style_metrics

SAMPLE_USER_CHAT = """
09/09/26, 2:30 PM - Rahul: Bro where are you?
09/09/26, 2:31 PM - Lokesh: Coming ra 😂
09/09/26, 2:32 PM - Lokesh: Enti mama late ayyindhi
09/09/26, 2:33 PM - Rahul: Fast ga ra.
09/09/26, 2:35 PM - Lokesh: Reached ra!!
"""

def test_extract_style_metrics():
    messages = parse_whatsapp_chat(SAMPLE_USER_CHAT, conversation_id="rahul_123", user_name="Lokesh")
    user_msgs = [m for m in messages if m.is_user]
    
    metrics = extract_style_metrics(user_msgs)
    
    assert metrics["code_switch_ratio"] > 0.0
    assert "ra" in metrics["slang_words"]
    assert "😂" in metrics["emoji_dist"]
    assert metrics["avg_sentence_len"] > 0.0
