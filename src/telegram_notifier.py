import json
import sqlite3
import datetime
import re
from typing import List, Dict, Any, Optional
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.dynamic_rag_engine import DynamicRAGEngine

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'([_*\[\]()~>#+\-=|{}.!\\`])', r'\\\1', str(text))

class TelegramApprovalNotifier:
    """
    Handles Telegram Human-In-The-Loop Approval notifications for intercepted WhatsApp messages.
    Formats multi-choice quick action buttons + custom message prompt.
    """
    def __init__(self, db_path: str = "live_whatsapp.db"):
        self.db_path = db_path
        self.queue = HumanApprovalQueue(db_path)
        self.dynamic_rag = DynamicRAGEngine(db_path)

    def generate_candidate_options(
        self,
        incoming_message: str,
        contact_id: str,
        candidate_response: Optional[str] = None
    ) -> List[str]:
        """
        Generates contextual candidate choices tailored specifically to the incoming message topic.
        If candidate_response is provided, Option 1 is set to the candidate response.
        """
        lower_inc = incoming_message.lower()

        if any(w in lower_inc for w in ["em chestunnav", "em chestav", "em chestunav", "wassup", "what are you doing"]):
            contextual = [
                "Em ledhu ra, work chusthunna... nuvv?",
                "Chinna project work lo unna ra",
                "Em ledhu, kaliga unna... cheppu"
            ]
        elif any(w in lower_inc for w in ["movie", "eldham", "eldhama", "vosthava", "osthava"]):
            contextual = [
                "Ha ready eh raa, eppudu eldham?",
                "Ledhu ra, koncham work unna late avthadhi",
                "Sarle, plan set chesi cheppu"
            ]
        elif any(w in lower_inc for w in ["kaali", "free", "repu", "time"]):
            contextual = [
                "Ha kaali eh raa... 9 ki ostha",
                "Ledhu ra, work unna morning... tarvata matladadam",
                "Sarle, confirm chesi cheptha 10 mins lo"
            ]
        elif any(w in lower_inc for w in ["accident", "emergency", "hospital", "police", "danger", "help"]):
            contextual = [
                "Rey ekkada unnav? Osthunna ipude!",
                "Em ayindhi ra? Everything fine?",
                "Rey call chestha undu 1 min"
            ]
        elif any(w in lower_inc for w in ["money", "rupees", "transfer", "upi", "gpay", "phonepe", "kotam"]):
            contextual = [
                "Ha gpay chestha aagu",
                "Ledhu ra account lo levu ippud",
                "Enti katha? call cheyyi okasari"
            ]
        else:
            contextual = [
                "Ha sare raa",
                "Oddu le ra",
                "Enti katha? cheppu"
            ]

        if candidate_response and candidate_response.strip():
            clean_cand = candidate_response.strip()
            # If Option 1 is set to the AI candidate response, update options 2 & 3 to matching contextual choices
            options = [clean_cand]
            for opt in contextual:
                if opt.strip().lower() != clean_cand.lower() and opt not in options:
                    options.append(opt)
                if len(options) >= 3:
                    break
            return options
        return contextual

    def format_telegram_notification(self, queue_id: str) -> Dict[str, Any]:
        """
        Formats the interactive Telegram message card for the intercepted WhatsApp message.
        """
        item = self.queue.get_item(queue_id)
        if not item:
            raise ValueError(f"Queue ID {queue_id} not found")

        options = self.generate_candidate_options(
            incoming_message=item.incoming_message,
            contact_id=item.contact_id,
            candidate_response=item.candidate_response
        )

        clean_contact = escape_markdown(item.contact_id)
        clean_msg = escape_markdown(item.incoming_message)
        clean_reason = escape_markdown(item.reason or "")
        clean_candidate = escape_markdown(item.candidate_response)

        card_text = (
            f"🚨 *WHATSAPP DECISION INTERCEPTED*\n"
            f"───────────────────────────\n"
            f"👤 *From Contact:* `{clean_contact}`\n"
            f"💬 *Message:* \"{clean_msg}\"\n"
            f"⚠️ *Reason:* {clean_reason}\n\n"
            f"🤖 *AI Candidate Reply:* \"{clean_candidate}\"\n\n"
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
