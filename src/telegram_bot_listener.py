import os
import re
import time
import json
import sqlite3
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.telegram_notifier import TelegramApprovalNotifier
from src.interaction_rag import InteractionRAG
from src.learning_pipeline import ContinuousLearningPipeline

logger = logging.getLogger(__name__)

class TelegramBotListener:
    """
    Dedicated Long-Polling Listener for Telegram Approval Bot.
    - Polls callback queries (button clicks) and custom text messages directly over HTTPS.
    - Operates completely independently without webhooks or public tunnels.
    - Immediately answers callback queries (clearing loading spinners).
    - Posts approved messages to WhatsApp via local Baileys bridge (http://localhost:3000/send).
    - Edits Telegram approval cards to confirm delivery status.
    """
    def __init__(self, bot_token: Optional[str] = None, db_path: str = "live_whatsapp.db", bridge_url: str = "http://localhost:3000"):
        self.db_path = db_path
        self.bridge_url = bridge_url
        self.queue = HumanApprovalQueue(db_path)
        self.notifier = TelegramApprovalNotifier(db_path)
        self.rag = InteractionRAG(db_path)
        self.learning = ContinuousLearningPipeline(self.rag)
        
        # Load environment variables
        env_file = Path("/home/lokesh/projects/whatsapp-agent/.env")
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ.setdefault(k, v.strip("\"'"))

        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        self.last_update_id = 0
        self.pending_custom_replies: Dict[str, str] = {}  # telegram_chat_id -> queue_id
        self.running = False

    def _to_whatsapp_jid(self, contact_id: str) -> str:
        cid = str(contact_id).strip()
        if cid.endswith("@lid") or cid.endswith("@s.whatsapp.net") or cid.endswith("@g.us"):
            return cid
        clean = re.sub(r'[^0-9]', '', cid)
        if clean and len(clean) >= 10:
            if not clean.startswith("91") and len(clean) == 10:
                clean = "91" + clean
            return f"{clean}@s.whatsapp.net"
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            row = cur.execute(
                "SELECT contact_id FROM reconstructed_interactions WHERE contact_id LIKE ? ORDER BY timestamp DESC LIMIT 1",
                (f"%{cid}%",)
            ).fetchone()
            conn.close()
            if row and row[0]:
                return self._to_whatsapp_jid(row[0])
        except Exception:
            pass
        return cid

    def _api_call(self, method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.bot_token:
            return None
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("Telegram API call error (%s): %s", method, e)
            return None

    def answer_callback_query(self, callback_query_id: str, text: str = "Processing approval..."):
        self._api_call("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text
        })

    def edit_message_text(self, chat_id: Any, message_id: int, text: str):
        self._api_call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        })

    def send_whatsapp_message(self, contact_id: str, message_text: str) -> bool:
        """
        Posts the approved reply directly to WhatsApp via local Baileys bridge (http://localhost:3000/send).
        """
        jid = self._to_whatsapp_jid(contact_id)
        payload = {
            "chatId": jid,
            "message": message_text
        }
        url = f"{self.bridge_url}/send"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("status") == "success" or data.get("success") is True or "messageId" in data or resp.status == 200
        except Exception as e:
            logger.error("Error sending WhatsApp message via bridge: %s", e)
            return False

    def process_update(self, update: Dict[str, Any]):
        update_id = update.get("update_id", 0)
        if update_id > self.last_update_id:
            self.last_update_id = update_id

        # 1. Handle Inline Button Click (callback_query)
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            cb_data = cb.get("data", "")
            msg = cb.get("message", {})
            msg_id = msg.get("message_id")
            chat_id = msg.get("chat", {}).get("id")

            # Answer query immediately to clear loading spinner on mobile/desktop
            self.answer_callback_query(cb_id, "Action received!")

            if cb_data.startswith("approve_"):
                parts = cb_data.split("_")
                opt_idx = int(parts[-1]) if parts[-1].isdigit() else 1
                queue_id = "_".join(parts[1:-1])

                item = self.queue.get_item(queue_id)
                if item:
                    card_info = self.notifier.format_telegram_notification(queue_id)
                    options = card_info.get("options", [])
                    chosen_reply = options[opt_idx - 1] if 1 <= opt_idx <= len(options) else item.candidate_response

                    # Deliver to WhatsApp
                    sent_ok = self.send_whatsapp_message(item.contact_id, chosen_reply)

                    # Update status in SQLite & RAG
                    self.queue.update_status(queue_id, "APPROVE")
                    self.learning.record_human_edit_delta(item, chosen_reply)

                    # Update Telegram Card text with confirmation
                    status_text = "✅ DELIVERED TO WHATSAPP" if sent_ok else "⚠️ QUEUED FOR WHATSAPP DELIVERY"
                    updated_card = (
                        f"{status_text}\n"
                        f"───────────────────────────\n"
                        f"👤 *To Contact:* `{item.contact_id}`\n"
                        f"💬 *Original Prompt:* \"{item.incoming_message}\"\n"
                        f"📤 *Sent Response:* \"{chosen_reply}\""
                    )
                    self.edit_message_text(chat_id, msg_id, updated_card)
                else:
                    self._api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"⚠️ Item `{queue_id}` not found in queue. It may have expired or been processed."
                    })

            elif cb_data.startswith("custom_"):
                parts = cb_data.split("_")
                queue_id = "_".join(parts[1:])
                item = self.queue.get_item(queue_id)
                if item:
                    self.pending_custom_replies[str(chat_id)] = queue_id
                    custom_prompt = (
                        f"✏️ *CUSTOM RESPONSE REQUESTED*\n"
                        f"───────────────────────────\n"
                        f"👤 *To Contact:* `{item.contact_id}`\n"
                        f"💬 *Incoming Message:* \"{item.incoming_message}\"\n\n"
                        f"👇 *Type your custom reply in this chat to send to WhatsApp:*"
                    )
                    self.edit_message_text(chat_id, msg_id, custom_prompt)

        # 2. Handle Custom Message Text Input
        elif "message" in update:
            msg = update["message"]
            chat_id = str(msg.get("chat", {}).get("id"))
            text = msg.get("text", "").strip()

            if chat_id in self.pending_custom_replies and text:
                queue_id = self.pending_custom_replies.pop(chat_id)
                item = self.queue.get_item(queue_id)
                if item:
                    sent_ok = self.send_whatsapp_message(item.contact_id, text)
                    self.queue.update_status(queue_id, "EDIT", edited_text=text)
                    self.learning.record_human_edit_delta(item, text)

                    status_text = "✅ CUSTOM MESSAGE DELIVERED TO WHATSAPP" if sent_ok else "⚠️ QUEUED FOR WHATSAPP"
                    confirm_msg = (
                        f"{status_text}\n"
                        f"───────────────────────────\n"
                        f"👤 *To Contact:* `{item.contact_id}`\n"
                        f"📤 *Sent Reply:* \"{text}\""
                    )
                    self._api_call("sendMessage", {"chat_id": chat_id, "text": confirm_msg, "parse_mode": "Markdown"})

    def poll_once(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?offset={self.last_update_id + 1}&timeout=5"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    for update in data.get("result", []):
                        self.process_update(update)
        except Exception as e:
            logger.debug("Telegram poll error: %s", e)

    def start_polling_loop(self):
        self.running = True
        logger.info("Starting Dedicated Telegram Approval Bot Polling Loop...")
        print("🚀 Dedicated Telegram Approval Bot Poller active! (No tunnels required)")
        while self.running:
            self.poll_once()
            time.sleep(1)

if __name__ == "__main__":
    listener = TelegramBotListener()
    print("Running Telegram Approval Bot polling loop...")
    listener.start_polling_loop()
