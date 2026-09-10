import pytest
from src.telegram_bridge import TelegramGatewayBridge

def test_telegram_bridge_intercept_and_resolve(tmp_path):
    db_file = str(tmp_path / "bridge_test.db")
    bridge = TelegramGatewayBridge(db_path=db_file)

    # 1. Test Inbound Interception (repu 9 ki kaali eh na?)
    inbound_res = bridge.handle_inbound_whatsapp(
        contact_name="Frndu",
        incoming_text="repu 9 ki kaali eh na?",
        candidate_response="ha ready eh 🫠"
    )

    assert inbound_res["action"] == "TELEGRAM_NOTIFY_AND_HOLD"
    assert inbound_res["whatsapp_response"] is None  # Held from WhatsApp
    assert inbound_res["telegram_payload"] is not None

    card = inbound_res["telegram_payload"]
    assert "repu 9 ki kaali eh na?" in card["text"]
    assert len(card["buttons"]) == 4

    qid = inbound_res["queue_id"]

    # 2. Test User selecting Option 1 via Telegram callback button
    resolve_res = bridge.resolve_telegram_callback(queue_id=qid, selected_option_index=1)

    assert resolve_res["status"] == "APPROVED_AND_SENT"
    assert "Ha kaali eh raa... 9 ki ostha" in resolve_res["final_whatsapp_message"]

def test_telegram_bridge_custom_message_resolution(tmp_path):
    db_file = str(tmp_path / "bridge_custom_test.db")
    bridge = TelegramGatewayBridge(db_path=db_file)

    inbound_res = bridge.handle_inbound_whatsapp(
        contact_name="Abhiii",
        incoming_text="5:00 ki ready eh na?",
        candidate_response="ha ready eh"
    )

    qid = inbound_res["queue_id"]

    # User inputs custom text
    resolve_res = bridge.resolve_telegram_callback(
        queue_id=qid,
        selected_option_index=4,
        custom_text="Ledhu 5:30 ki ostha"
    )

    assert resolve_res["status"] == "APPROVED_AND_SENT"
    assert "Ledhu 5:30 ki ostha" in resolve_res["final_whatsapp_message"]
