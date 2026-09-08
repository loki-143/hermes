import pytest
from datetime import datetime
from src.db import init_db
from src.interaction_rag import InteractionRAG
from src.approval_queue import ApprovalItem
from src.learning_pipeline import ContinuousLearningPipeline

@pytest.fixture
def learning_setup(tmp_path):
    db_file = str(tmp_path / "test_learning.db")
    init_db(db_file)
    rag = InteractionRAG(db_path=db_file)
    pipeline = ContinuousLearningPipeline(rag_engine=rag)
    return rag, pipeline

def test_record_human_edit_delta(learning_setup):
    rag, pipeline = learning_setup
    
    item = ApprovalItem(
        queue_id="q_100",
        contact_id="rahul_123",
        incoming_message="Where are you bro?",
        candidate_response="I am coming soon.",
        risk_level="low"
    )
    
    pipeline.record_human_edit_delta(item, final_user_text="Coming ra 🚗")
    
    # Search RAG to confirm new interaction was learned
    results = rag.search_similar_interactions("where bro", contact_id="rahul_123")
    assert len(results) == 1
    assert results[0].user_response == "Coming ra 🚗"
