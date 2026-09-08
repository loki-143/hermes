import os
import pytest
import sqlite3
from src.db import init_db
from src.models import ContactProfile, NormalizedMessage, ReconstructedInteraction, MemoryItem
from datetime import datetime

@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_whatsapp_agent.db")
    init_db(db_file)
    return db_file

def test_db_initialization(test_db):
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()
    
    assert "contacts" in tables
    assert "normalized_messages" in tables
    assert "reconstructed_interactions" in tables
    assert "memories" in tables
    assert "global_style" in tables
    assert "interactions_fts" in tables

def test_contact_profile_model():
    contact = ContactProfile(
        contact_id="919876543210",
        display_name="Rahul",
        relationship_category="close_friend",
        formality_score=0.1,
        top_emojis=["😂", "🚗"]
    )
    assert contact.contact_id == "919876543210"
    assert contact.relationship_category == "close_friend"
    assert len(contact.top_emojis) == 2

def test_interaction_model():
    now = datetime.now()
    interaction = ReconstructedInteraction(
        interaction_id="inter_1",
        contact_id="919876543210",
        incoming_message="Where are you?",
        user_response="Coming ra 😂",
        relationship_category="close_friend",
        timestamp=now
    )
    assert interaction.interaction_id == "inter_1"
    assert interaction.user_response == "Coming ra 😂"
