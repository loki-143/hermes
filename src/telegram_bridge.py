import sqlite3
import datetime
from typing import Dict, Any, Optional, List
from src.whatsapp_gateway import WhatsAppGatewayHandler
from src.telegram_notifier import TelegramApprovalNotifier
from src.approval_queue import HumanApprovalQueue

class TelegramGatewayBridge:
    """
    Bridge module connecting WhatsApp Gateway risk events directly with
    Telegram Bot API delivery and callback button handling.
    """
    def __init__(self, db_path: str = "live_whatsapp.db"):
        self.db_path = db_path
        self.gw = WhatsAppGatewayHandler(db_path=db_path)
        self.notifier = TelegramApprovalNotifier(db_path=db_path)
        self.queue = HumanApprovalQueue(db_path=db_path)

    def handle_inbound_whatsapp(self, contact_name: str, incoming_text: str, candidate_response: str) -> Dict[str, Any]:
        """
        Processes an incoming WhatsApp message:
        - Low Risk -> Returns AUTO_SENT payload directly for WhatsApp output.
        - High/Medium Risk -> Holds message in queue, generates Telegram notification payload.
        """
        res = self.gw.process_incoming_message(
            contact_name=contact_name,
            incoming_text=incoming_text,
            candidate_response=candidate_response
        )

        if res["status"] == "APPROVAL_REQUIRED":
            telegram_card = self.notifier.format_telegram_notification(res["queue_id"])
            return {
                "action": "TELEGRAM_NOTIFY_AND_HOLD",
                "queue_id": res["queue_id"],
                "contact_name": contact_name,
                "incoming_text": incoming_text,
                "whatsapp_response": None,  # DO NOT SEND TO WHATSAPP YET
                "telegram_payload": telegram_card
            }
        else:
            return {
                "action": "AUTO_SEND_WHATSAPP",
                "contact_name": contact_name,
                "incoming_text": incoming_text,
                "whatsapp_response": res["outbound_text"],
                "telegram_payload": None
            }

    def resolve_telegram_callback(self, queue_id: str, selected_option_index: int, custom_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Handles Telegram button taps / custom message inputs:
        - Updates approval queue status.
        - Unblocks WhatsApp reply and delivers selected/edited response.
        - Indexes chosen response into RAG for continuous learning.
        """
        item = self.queue.get_item(queue_id)
        if not item:
            return {"status": "ERROR", "reason": "Item not found in approval queue"}

        if custom_text:
            final_reply = custom_text
            action = "EDIT"
        else:
            card = self.notifier.format_telegram_notification(queue_id)
            if 1 <= selected_option_index <= len(card["options"]):
                final_reply = card["options"][selected_option_index - 1]
                action = "APPROVE"
            else:
                final_reply = item.candidate_response
                action = "APPROVE"

        # Update Queue & Continuous Learning
        self.queue.update_status(queue_id, action, edited_text=final_reply if action == "EDIT" else None)

        outbound_tag = f"[Generated via {item.contact_id} persona (Human Approved)]"
        final_whatsapp_message = f"{final_reply}\n\n{outbound_tag}"

        return {
            "status": "APPROVED_AND_SENT",
            "queue_id": queue_id,
            "contact_name": item.contact_id,
            "final_whatsapp_message": final_whatsapp_message,
            "action_taken": action
        }
