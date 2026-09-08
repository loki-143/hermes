import pytest
from datetime import datetime
from src.db import init_db
from src.models import ReconstructedInteraction
from src.interaction_rag import InteractionRAG

@pytest.fixture
def rag_engine(tmp_path):
    db_file = str(tmp_path / "test_rag.db")
    init_db(db_file)
    return InteractionRAG(db_path=db_file)

def test_index_and_search_interactions(rag_engine):
    interaction1 = ReconstructedInteraction(
        interaction_id="inter_1",
        contact_id="rahul_123",
        incoming_message="Bro where are you waiting?",
        context_history=["Rahul: I am near cafe"],
        user_response="Coming ra 😂",
        relationship_category="close_friend",
        timestamp=datetime.now()
    )
    interaction2 = ReconstructedInteraction(
        interaction_id="inter_2",
        contact_id="prof_456",
        incoming_message="Please send your project report.",
        context_history=[],
        user_response="Yes sir, sending now.",
        relationship_category="formal_professional",
        timestamp=datetime.now()
    )

    rag_engine.index_interaction(interaction1)
    rag_engine.index_interaction(interaction2)

    # Search for "where waiting"
    results = rag_engine.search_similar_interactions("where waiting", contact_id="rahul_123")
    assert len(results) == 1
    assert results[0].interaction_id == "inter_1"
    assert results[0].user_response == "Coming ra 😂"

    # Search for "report"
    results_prof = rag_engine.search_similar_interactions("project report")
    assert len(results_prof) == 1
    assert results_prof[0].user_response == "Yes sir, sending now."
