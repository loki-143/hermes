import pytest
from src.ingestion import parse_whatsapp_chat
from src.relationship_engine import analyze_relationship_profile

FRIEND_CHAT = """
09/09/26, 2:30 PM - Rahul: Bro where are you?
09/09/26, 2:31 PM - Lokesh: Coming ra 😂
"""

PROFESSOR_CHAT = """
09/09/26, 3:00 PM - Prof Smith: Please submit your assignment by evening.
09/09/26, 3:05 PM - Lokesh: Yes sir, I will submit the assignment by 5 PM. Thank you.
"""

def test_relationship_profile_friend():
    msgs = parse_whatsapp_chat(FRIEND_CHAT, conversation_id="rahul_123", user_name="Lokesh")
    profile = analyze_relationship_profile(contact_id="rahul_123", display_name="Rahul", messages=msgs)
    
    assert profile.relationship_category == "close_friend"
    assert profile.formality_score <= 0.2
    assert "ra" in profile.preferred_greetings

def test_relationship_profile_professor():
    msgs = parse_whatsapp_chat(PROFESSOR_CHAT, conversation_id="prof_456", user_name="Lokesh")
    profile = analyze_relationship_profile(contact_id="prof_456", display_name="Prof Smith", messages=msgs)
    
    assert profile.relationship_category == "formal_professional"
    assert profile.formality_score >= 0.5
    assert "sir" in profile.preferred_greetings
