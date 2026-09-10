import pytest
from src.telegram_bot_listener import TelegramBotListener
from src.approval_queue import HumanApprovalQueue, ApprovalItem

def test_telegram_bot_listener_initialization(tmp_path):
    db_file = str(tmp_path / "listener_test.db")
    listener = TelegramBotListener(bot_token="TEST_TOKEN", db_path=db_file)
    assert listener.bot_token == "TEST_TOKEN"
    assert listener.bridge_url == "http://localhost:3000"

def test_telegram_bot_listener_jid_format():
    listener = TelegramBotListener(bot_token="TEST")
    jid1 = listener._to_whatsapp_jid("918332937780")
    assert jid1 == "918332937780@s.whatsapp.net"
