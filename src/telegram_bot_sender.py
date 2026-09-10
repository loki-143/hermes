import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.telegram_notifier import TelegramApprovalNotifier

class TelegramBotSender:
    """
    Direct Telegram Bot API sender that posts Inline Keyboard Cards to Telegram
    and processes callback button selections.
    """
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, db_path: str = "live_whatsapp.db"):
        # Load local .env if env vars not in os.environ
        from pathlib import Path
        env_file = Path("/home/lokesh/projects/whatsapp-agent/.env")
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ.setdefault(k, v.strip("\"'"))

        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "5450924116")
        self.db_path = db_path
        self.notifier = TelegramApprovalNotifier(db_path=db_path)
        self.queue = HumanApprovalQueue(db_path=db_path)

    def send_telegram_card(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """
        Sends an interactive Telegram Card with inline keyboard buttons to your Telegram chat.
        """
        if not self.bot_token:
            print("⚠️ TELEGRAM_BOT_TOKEN not configured. Card notification logged locally.")
            return None

        card_data = self.notifier.format_telegram_notification(queue_id)
        
        # Build Inline Keyboard Markup for Telegram Bot API
        inline_keyboard = []
        for b in card_data["buttons"]:
            inline_keyboard.append([{"text": b["text"], "callback_data": b["callback_data"]}])

        payload = {
            "chat_id": self.chat_id,
            "text": card_data["text"],
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": inline_keyboard
            }
        }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            print(f"❌ Error sending Telegram card: {e}")
            return None

if __name__ == "__main__":
    sender = TelegramBotSender()
    print("TelegramBotSender initialized.")
