import os
import json
import pytest
from unittest.mock import patch
from src.cli import main
from src.approval_queue import HumanApprovalQueue, ApprovalItem


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_cli.db")
    return db_file


def test_cli_init_db(temp_db, capsys):
    test_args = ["whatsapp-agent", "--db-path", temp_db, "init-db"]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Database initialized successfully" in captured.out
    assert os.path.exists(temp_db)


def test_cli_ingest(temp_db, tmp_path, capsys):
    chat_file = tmp_path / "chat.txt"
    chat_file.write_text(
        "09/09/26, 2:30 PM - Rahul: Hey bro are you coming?\n"
        "09/09/26, 2:31 PM - User: Yes ra coming now 🚗\n",
        encoding="utf-8"
    )
    test_args = [
        "whatsapp-agent", "--db-path", temp_db,
        "ingest", str(chat_file),
        "--conversation-id", "conv_100",
        "--contact-id", "contact_rahul",
        "--contact-name", "Rahul",
        "--user-name", "User"
    ]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Ingested 2 messages" in captured.out
    assert "Reconstructed 1 interaction tuples" in captured.out


def test_cli_eval_risk(capsys):
    test_args = [
        "whatsapp-agent",
        "eval-risk",
        "Can you send 1000 rupees via UPI?",
        "Sure sending now"
    ]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Decision: HUMAN_ONLY" in captured.out
    assert "Risk Level: high" in captured.out


def test_cli_pending_and_process_approval(temp_db, capsys):
    queue = HumanApprovalQueue(db_path=temp_db)
    queue.enqueue(ApprovalItem(
        queue_id="item_1",
        contact_id="contact_rahul",
        incoming_message="Schedule meeting?",
        candidate_response="Yes tomorrow",
        risk_level="medium",
        status="PENDING"
    ))

    # Pending approvals
    test_args = ["whatsapp-agent", "--db-path", temp_db, "pending-approvals"]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Found 1 pending item(s)" in captured.out
    assert "item_1" in captured.out

    # Process approval - APPROVE
    test_args = ["whatsapp-agent", "--db-path", temp_db, "process-approval", "item_1", "APPROVE"]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Updated item 'item_1' with action 'APPROVE'" in captured.out

    # Check pending again
    test_args = ["whatsapp-agent", "--db-path", temp_db, "pending-approvals"]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Found 0 pending item(s)" in captured.out


def test_cli_run_eval(capsys):
    test_args = ["whatsapp-agent", "run-eval"]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert "Evaluation Accuracy: 100.0%" in captured.out


def test_cli_export_ft(temp_db, tmp_path, capsys):
    out_jsonl = str(tmp_path / "ft_data.jsonl")
    test_args = ["whatsapp-agent", "--db-path", temp_db, "export-ft", out_jsonl]
    with patch("sys.argv", test_args):
        main()
    captured = capsys.readouterr()
    assert f"Exported 0 fine-tuning examples to '{out_jsonl}'" in captured.out
    assert os.path.exists(out_jsonl)
