import pytest
from src.risk_engine import evaluate_response_risk
from src.whatsapp_gateway import WhatsAppGatewayHandler
from src.telegram_notifier import TelegramApprovalNotifier
from src.approval_queue import HumanApprovalQueue

def test_scheduling_risk_detection():
    # Test Telugu scheduling keywords "repu" and "kaali"
    decision = evaluate_response_risk(
        incoming_message="repu 9 ki kaali eh na?",
        candidate_response="ha kaali eh raa... 9 ki ostha"
    )
    assert decision.decision == "REVIEW"
    assert decision.risk_level == "medium"

def test_telegram_notification_formatting(tmp_path):
    db_file = str(tmp_path / "test_notifier.db")
    gw = WhatsAppGatewayHandler(db_path=db_file)
    notifier = TelegramApprovalNotifier(db_path=db_file)

    res = gw.process_incoming_message(
        contact_name="Frndu",
        incoming_text="repu 9 ki kaali eh na?",
        candidate_response="ha kaali eh raa"
    )

    assert res["status"] == "APPROVAL_REQUIRED"
    card = notifier.format_telegram_notification(res["queue_id"])

    assert "repu 9 ki kaali eh na?" in card["text"]
    assert len(card["buttons"]) == 4  # 3 options + 1 Custom Message button
    assert card["buttons"][-1]["text"] == "✏️ Custom Message"
