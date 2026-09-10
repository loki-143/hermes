import json
import sqlite3
import datetime
from typing import List, Dict, Any, Optional
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.dynamic_rag_engine import DynamicRAGEngine

class TelegramApprovalNotifier:
    """
    Handles Telegram Human-In-The-Loop Approval notifications for intercepted WhatsApp messages.
    Formats multi-choice quick action buttons + custom message prompt.
    """
    def __init__(self, db_path: str = "live_whatsapp.db"):
        self.db_path = db_path
        self.queue = HumanApprovalQueue(db_path)
        self.dynamic_rag = DynamicRAGEngine(db_path)

    def generate_candidate_options(self, incoming_message: str, contact_id: str) -> List[str]:
        """
        Generates 2-3 contextual candidate choices (Yes/No/Tentative) in Loki's authentic style.
        """
        lower_inc = incoming_message.lower()

        # Availability / Scheduling queries (e.g. repu 9 ki kaali eh na)
        if any(w in lower_inc for w in ["kaali", "free", "repu", "9", "time", "ready", "eldhama"]):
            return [
                "Ha kaali eh raa... 9 ki ostha",
                "Ledhu ra, work unna morning... tarvata matladadam",
                "Sarle, confirm chesi cheptha 10 mins lo"
            ]
        # Financial / Request queries
        elif any(w in lower_inc for w in ["money", "rupees", "transfer", "upi"]):
            return [
                "Ha gpay chestha aagu",
                "Ledhu ra account lo levu ippud",
                "Enti katha? call cheyyi okasari"
            ]
        # General Decision queries
        else:
            return [
                "Ha sare raa",
                "Oddu le ra",
                "Enti katha?"
            ]

    def format_telegram_notification(self, queue_id: str) -> Dict[str, Any]:
        """
        Formats the interactive Telegram message card for the intercepted WhatsApp message.
        """
        item = self.queue.get_item(queue_id)
        if not item:
            raise ValueError(f"Queue ID {queue_id} not found")

        options = self.generate_candidate_options(item.incoming_message, item.contact_id)

        card_text = (
            f"🚨 *WHATSAPP DECISION INTERCEPTED*\n"
            f"───────────────────────────\n"
            f"👤 *From Contact:* `{item.contact_id}`\n"
            f"💬 *Message:* \"{item.incoming_message}\"\n"
            f"⚠️ *Reason:* {item.reason}\n\n"
            f"🤖 *AI Candidate Reply:* \"{item.candidate_response}\"\n\n"
            f"👇 *Choose an option or type a custom reply:*"
        )

        buttons = []
        for idx, opt in enumerate(options, 1):
            buttons.append({"text": f"{idx}. {opt}", "callback_data": f"approve_{queue_id}_{idx}"})

        buttons.append({"text": "✏️ Custom Message", "callback_data": f"custom_{queue_id}"})

        return {
            "queue_id": queue_id,
            "text": card_text,
            "options": options,
            "buttons": buttons
        }

if __name__ == "__main__":
    notifier = TelegramApprovalNotifier()
    # Test notification format
    dummy_item = ApprovalItem(
        queue_id="gate_test_123",
        contact_id="Frndu",
        incoming_message="repu 9 ki kaali eh na?",
        candidate_response="ha kaali eh raa",
        risk_level="medium",
        reason="Time commitment / specific time pattern (9)",
        status="PENDING"
    )
    notifier.queue.enqueue(dummy_item)
    notification = notifier.format_telegram_notification("gate_test_123")
    print(json.dumps(notification, indent=2))
