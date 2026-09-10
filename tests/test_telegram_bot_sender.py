import pytest
from src.telegram_bot_sender import TelegramBotSender
from src.approval_queue import HumanApprovalQueue, ApprovalItem

def test_telegram_bot_sender_initialization(tmp_path):
    db_file = str(tmp_path / "bot_test.db")
    sender = TelegramBotSender(bot_token="TEST_TOKEN", chat_id="5450924116", db_path=db_file)
    assert sender.bot_token == "TEST_TOKEN"
    assert sender.chat_id == "5450924116"

def test_telegram_bot_sender_missing_token(tmp_path):
    db_file = str(tmp_path / "bot_test2.db")
    queue = HumanApprovalQueue(db_file)
    item = ApprovalItem(
        queue_id="gate_test_999",
        contact_id="Frndu",
        incoming_message="repu mrng movie ki eldham",
        candidate_response="ha ready eh 🫠",
        risk_level="medium",
        reason="Real-world decision detected: Movie plan",
        status="PENDING"
    )
    queue.enqueue(item)

    sender = TelegramBotSender(bot_token=None, chat_id="5450924116", db_path=db_file)
    res = sender.send_telegram_card("gate_test_999")
    assert res is None
