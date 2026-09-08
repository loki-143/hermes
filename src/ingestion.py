import re
from datetime import datetime
from typing import List, Optional
from src.models import NormalizedMessage, ReconstructedInteraction

# Match standard WhatsApp export lines:
# e.g., "09/09/26, 2:30 PM - Rahul: Bro where are you?"
# e.g., "[09/09/26, 14:30:00] Rahul: Bro where are you?"
LINE_PATTERN = re.compile(
    r"^(?:\[?(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]?)\s*-\s*([^:]+):\s*(.*)$",
    re.IGNORECASE
)

DATE_FORMATS = [
    "%d/%m/%y, %I:%M %p",
    "%m/%d/%y, %I:%M %p",
    "%d/%m/%Y, %I:%M %p",
    "%d/%m/%y, %H:%M:%S",
    "%d/%m/%Y, %H:%M:%S",
    "%d/%m/%y, %H:%M",
]

def parse_datetime(dt_str: str) -> datetime:
    dt_str = dt_str.strip("[] ").replace("\u202f", " ")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return datetime.now()

def parse_whatsapp_chat(
    chat_text: str,
    conversation_id: str,
    user_name: str
) -> List[NormalizedMessage]:
    lines = chat_text.splitlines()
    messages: List[NormalizedMessage] = []
    
    msg_counter = 0
    current_msg: Optional[dict] = None

    for line in lines:
        match = LINE_PATTERN.match(line.strip())
        if match:
            if current_msg:
                messages.append(NormalizedMessage(**current_msg))
            
            dt_raw, sender, text = match.groups()
            msg_counter += 1
            msg_id = f"{conversation_id}_{msg_counter}"
            sender_clean = sender.strip()
            is_user = (sender_clean.lower() == user_name.lower())
            
            current_msg = {
                "message_id": msg_id,
                "conversation_id": conversation_id,
                "sender_id": sender_clean,
                "sender_name": sender_clean,
                "message_text": text.strip(),
                "is_user": is_user,
                "timestamp": parse_datetime(dt_raw),
                "reply_to_id": None,
                "metadata": {}
            }
        elif current_msg:
            # Continuation line
            current_msg["message_text"] += "\n" + line.strip()

    if current_msg:
        messages.append(NormalizedMessage(**current_msg))

    return messages

def reconstruct_interactions(
    messages: List[NormalizedMessage],
    contact_id: str,
    relationship_category: str = "friend"
) -> List[ReconstructedInteraction]:
    interactions: List[ReconstructedInteraction] = []
    
    context_buffer: List[str] = []
    pending_incoming: Optional[NormalizedMessage] = None

    for msg in messages:
        if not msg.is_user:
            if pending_incoming:
                context_buffer.append(f"{pending_incoming.sender_name}: {pending_incoming.message_text}")
                if len(context_buffer) > 5:
                    context_buffer.pop(0)
            pending_incoming = msg
        else:
            if pending_incoming:
                interaction_id = f"inter_{msg.message_id}"
                interactions.append(ReconstructedInteraction(
                    interaction_id=interaction_id,
                    contact_id=contact_id,
                    incoming_message=pending_incoming.message_text,
                    context_history=list(context_buffer),
                    user_response=msg.message_text,
                    relationship_category=relationship_category,
                    timestamp=msg.timestamp
                ))
                context_buffer.append(f"{pending_incoming.sender_name}: {pending_incoming.message_text}")
                context_buffer.append(f"User: {msg.message_text}")
                if len(context_buffer) > 5:
                    context_buffer = context_buffer[-5:]
                pending_incoming = None

    return interactions
