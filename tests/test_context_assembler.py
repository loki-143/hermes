import pytest
from datetime import datetime
from src.models import ContactProfile, MemoryItem, ReconstructedInteraction
from src.context_assembler import ContextAssembler

def test_context_assembler_prompt_and_turn():
    global_style = {
        "code_switch_ratio": 0.5,
        "slang_words": {"ra": 10, "bro": 5},
        "emoji_dist": {"😂": 8, "🚗": 4},
        "avg_sentence_len": 4.5
    }
    
    contact = ContactProfile(
        contact_id="rahul_123",
        display_name="Rahul",
        relationship_category="close_friend",
        formality_score=0.1,
        preferred_greetings=["ra", "bro"],
        top_emojis=["😂", "🚗"]
    )
    
    system_prompt = ContextAssembler.build_system_prompt(global_style, contact)
    assert "GLOBAL USER STYLE:" in system_prompt
    assert "CONTACT RELATIONSHIP:" in system_prompt
    assert "close_friend" in system_prompt
    assert "Code-Switching Rate: 0.5" in system_prompt

    memories = [
        MemoryItem(
            memory_id="m1",
            contact_id="rahul_123",
            memory_type="episodic",
            fact_summary="Rahul has a job interview on Monday."
        )
    ]
    
    similar_interactions = [
        ReconstructedInteraction(
            interaction_id="i1",
            contact_id="rahul_123",
            incoming_message="Bro where are you?",
            user_response="Coming ra 😂",
            relationship_category="close_friend",
            timestamp=datetime.now()
        )
    ]

    turn_context = ContextAssembler.build_turn_context(
        incoming_message="Bro when are you starting?",
        recent_history=["Rahul: I am ready at home."],
        memories=memories,
        similar_interactions=similar_interactions
    )

    assert "RELEVANT MEMORIES / FACTS:" in turn_context
    assert "Rahul has a job interview on Monday." in turn_context
    assert "SIMILAR PAST INTERACTIONS:" in turn_context
    assert "Coming ra 😂" in turn_context
    assert "CURRENT INCOMING MESSAGE:" in turn_context
