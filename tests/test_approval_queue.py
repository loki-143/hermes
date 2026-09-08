import pytest
from src.db import init_db
from src.approval_queue import HumanApprovalQueue, ApprovalItem

@pytest.fixture
def queue_db(tmp_path):
    db_file = str(tmp_path / "test_queue.db")
    init_db(db_file)
    return HumanApprovalQueue(db_path=db_file)

def test_enqueue_and_get_pending(queue_db):
    item = ApprovalItem(
        queue_id="q_1",
        contact_id="prof_456",
        incoming_message="Please submit your report.",
        candidate_response="Yes sir, sending now.",
        risk_level="medium"
    )
    queue_db.enqueue(item)
    
    pending = queue_db.get_pending_items()
    assert len(pending) == 1
    assert pending[0].queue_id == "q_1"
    assert pending[0].candidate_response == "Yes sir, sending now."

def test_approval_actions(queue_db):
    item = ApprovalItem(
        queue_id="q_2",
        contact_id="rahul_123",
        incoming_message="Can you pay me?",
        candidate_response="I will send money.",
        risk_level="high"
    )
    queue_db.enqueue(item)
    
    # Test EDIT action
    queue_db.update_status(queue_id="q_2", action="EDIT", edited_text="I will check and reply later.")
    
    pending = queue_db.get_pending_items()
    assert len(pending) == 0
