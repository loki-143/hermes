import pytest
from datetime import datetime
from src.db import init_db
from src.models import ReconstructedInteraction
from src.interaction_rag import InteractionRAG
from src.dynamic_rag_engine import DynamicRAGEngine

@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_dynamic_rag.db")
    init_db(db_file)
    return db_file

def test_dynamic_rag_fewshot_assembly(temp_db):
    rag = InteractionRAG(db_path=temp_db)
    
    interaction = ReconstructedInteraction(
        interaction_id="inter_100",
        contact_id="frndu",
        incoming_message="Babu online unnaara?",
        context_history=["Frndu: hey"],
        user_response="Ha unnan ra",
        relationship_category="close_friend",
        timestamp=datetime.now()
    )
    rag.index_interaction(interaction)

    engine = DynamicRAGEngine(db_path=temp_db)
    result = engine.assemble_fewshot_prompt(
        incoming_message="Babu online unnaara?",
        contact_id="frndu",
        recent_history=["frndu: hey man"],
        limit=5
    )

    assert "system_instruction" in result
    assert "user_prompt" in result
    assert "matched_interactions" in result
    assert len(result["matched_interactions"]) >= 1
    assert "EXACT HISTORICAL FEW-SHOT EXAMPLES" in result["system_instruction"]
    assert "RECENT CONVERSATION:" in result["user_prompt"]
    assert "INCOMING MESSAGE (frndu):" in result["user_prompt"]

def test_dynamic_rag_fallback_retrieval(temp_db):
    rag = InteractionRAG(db_path=temp_db)
    
    interaction = ReconstructedInteraction(
        interaction_id="inter_101",
        contact_id="abhi",
        incoming_message="Chai ki podham",
        context_history=[],
        user_response="Vostha 5 mins",
        relationship_category="close_friend",
        timestamp=datetime.now()
    )
    rag.index_interaction(interaction)

    engine = DynamicRAGEngine(db_path=temp_db)
    # Query string doesn't match FTS terms directly, fallback to contact history
    result = engine.assemble_fewshot_prompt(
        incoming_message="Unrelated random phrase 12345",
        contact_id="abhi",
        recent_history=[],
        limit=5
    )

    assert len(result["matched_interactions"]) == 1
    assert result["matched_interactions"][0]["user_response"] == "Vostha 5 mins"
