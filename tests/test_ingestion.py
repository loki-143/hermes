import pytest
from src.ingestion import parse_whatsapp_chat, reconstruct_interactions

SAMPLE_CHAT = """
09/09/26, 2:30 PM - Rahul: Bro where are you?
09/09/26, 2:31 PM - Rahul: We are waiting at the cafe.
09/09/26, 2:32 PM - Lokesh: Coming ra 😂
09/09/26, 2:33 PM - Lokesh: On my way, 5 mins.
09/09/26, 2:35 PM - Rahul: Okay hurry up.
09/09/26, 2:36 PM - Lokesh: Reached ra!
"""

def test_parse_whatsapp_chat():
    messages = parse_whatsapp_chat(SAMPLE_CHAT, conversation_id="rahul_123", user_name="Lokesh")
    assert len(messages) == 6
    assert messages[0].sender_name == "Rahul"
    assert messages[0].is_user is False
    assert messages[2].sender_name == "Lokesh"
    assert messages[2].is_user is True
    assert messages[2].message_text == "Coming ra 😂"

def test_reconstruct_interactions():
    messages = parse_whatsapp_chat(SAMPLE_CHAT, conversation_id="rahul_123", user_name="Lokesh")
    interactions = reconstruct_interactions(messages, contact_id="rahul_123", relationship_category="close_friend")
    
    assert len(interactions) == 2
    # Interaction 1: Rahul says "We are waiting at the cafe." -> User says "Coming ra 😂"
    assert interactions[0].incoming_message == "We are waiting at the cafe."
    assert interactions[0].user_response == "Coming ra 😂"
    assert interactions[0].relationship_category == "close_friend"
    
    # Interaction 2: Rahul says "Okay hurry up." -> User says "Reached ra!"
    assert interactions[1].incoming_message == "Okay hurry up."
    assert interactions[1].user_response == "Reached ra!"
