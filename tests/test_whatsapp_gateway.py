import pytest
from src.whatsapp_gateway import WhatsAppGatewayHandler
from src.approval_queue import HumanApprovalQueue

@pytest.fixture
def gateway(tmp_path):
    db_file = str(tmp_path / "test_gateway.db")
    skills_dir = str(tmp_path / "skills")
    return WhatsAppGatewayHandler(db_path=db_file, skills_dir=skills_dir)

def test_gateway_known_contact_routing(tmp_path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "lokesh-frndu-persona"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Frndu Persona Skill")

    gw = WhatsAppGatewayHandler(db_path=str(tmp_path / "test.db"), skills_dir=str(skills_dir))
    
    res = gw.process_incoming_message(
        contact_name="Frndu",
        incoming_text="Rey cheppu raww...",
        candidate_response="em ledhu ra... work lo unna 🫠"
    )

    assert res["status"] == "AUTO_SENT"
    assert res["is_known_contact"] is True
    assert "[Generated via lokesh-frndu-persona skill]" in res["outbound_text"]

def test_gateway_new_contact_onboarding(tmp_path):
    gw = WhatsAppGatewayHandler(db_path=str(tmp_path / "test_new.db"), skills_dir=str(tmp_path / "skills"))
    
    res = gw.process_incoming_message(
        contact_name="Rahul",
        incoming_text="Hi bro how are you?",
        candidate_response="Fine bro, what about you?"
    )

    assert res["status"] == "AUTO_SENT"
    assert res["is_known_contact"] is False
    assert "[Generated via learning engine (New Contact)]" in res["outbound_text"]

def test_gateway_risk_interception(tmp_path):
    gw = WhatsAppGatewayHandler(db_path=str(tmp_path / "test_risk.db"), skills_dir=str(tmp_path / "skills"))
    
    res = gw.process_incoming_message(
        contact_name="Frndu",
        incoming_text="ok aithe 5:00 ki ready eh na?",
        candidate_response="ha ready eh 🫠"
    )

    assert res["status"] == "APPROVAL_REQUIRED"
    assert res["risk_decision"]["decision"] == "REVIEW"
    assert "held for approval" in res["outbound_text"]

    queue = HumanApprovalQueue(str(tmp_path / "test_risk.db"))
    pending = queue.get_pending_items()
    assert len(pending) == 1
    assert pending[0].contact_id == "Frndu"
