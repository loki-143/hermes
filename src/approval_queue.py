import sqlite3
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class ApprovalItem(BaseModel):
    queue_id: str
    contact_id: str
    incoming_message: str
    candidate_response: str
    edited_response: Optional[str] = None
    risk_level: str
    reason: Optional[str] = None
    status: str = "PENDING"  # PENDING, APPROVED, EDITED, REJECTED, REGENERATED
    created_at: Optional[datetime] = None

class HumanApprovalQueue:
    def __init__(self, db_path: str = "whatsapp_agent.db"):
        self.db_path = db_path
        self._init_queue_table()

    def _init_queue_table(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approval_queue (
                queue_id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL,
                incoming_message TEXT NOT NULL,
                candidate_response TEXT NOT NULL,
                edited_response TEXT,
                risk_level TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def enqueue(self, item: ApprovalItem):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Add reason column if not exists
        try:
            cur.execute("ALTER TABLE approval_queue ADD COLUMN reason TEXT")
        except Exception:
            pass

        cur.execute("""
            INSERT OR REPLACE INTO approval_queue (
                queue_id, contact_id, incoming_message, candidate_response,
                edited_response, risk_level, reason, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.queue_id,
            item.contact_id,
            item.incoming_message,
            item.candidate_response,
            item.edited_response,
            item.risk_level,
            item.reason,
            item.status,
            item.created_at or datetime.now()
        ))
        conn.commit()
        conn.close()

    def get_item(self, queue_id: str) -> Optional[ApprovalItem]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT queue_id, contact_id, incoming_message, candidate_response,
                   edited_response, risk_level, reason, status, created_at
            FROM approval_queue
            WHERE queue_id = ?
        """, (queue_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return ApprovalItem(
            queue_id=row[0],
            contact_id=row[1],
            incoming_message=row[2],
            candidate_response=row[3],
            edited_response=row[4],
            risk_level=row[5],
            reason=row[6],
            status=row[7],
            created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8]
        )

    def get_pending_items(self) -> List[ApprovalItem]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT queue_id, contact_id, incoming_message, candidate_response,
                   edited_response, risk_level, status, created_at
            FROM approval_queue
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
        """)
        rows = cur.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append(ApprovalItem(
                queue_id=r[0],
                contact_id=r[1],
                incoming_message=r[2],
                candidate_response=r[3],
                edited_response=r[4],
                risk_level=r[5],
                status=r[6],
                created_at=datetime.fromisoformat(r[7]) if isinstance(r[7], str) else r[7]
            ))
        return items

    def update_status(self, queue_id: str, action: str, edited_text: Optional[str] = None):
        # action: APPROVE, EDIT, REJECT, REGENERATE
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if action == "EDIT" and edited_text:
            cur.execute("""
                UPDATE approval_queue
                SET status = 'EDITED', edited_response = ?
                WHERE queue_id = ?
            """, (edited_text, queue_id))
        elif action == "APPROVE":
            cur.execute("""
                UPDATE approval_queue
                SET status = 'APPROVED'
                WHERE queue_id = ?
            """, (queue_id,))
        elif action == "REJECT":
            cur.execute("""
                UPDATE approval_queue
                SET status = 'REJECTED'
                WHERE queue_id = ?
            """, (queue_id,))
        elif action == "REGENERATED":
            cur.execute("""
                UPDATE approval_queue
                SET status = 'REGENERATED'
                WHERE queue_id = ?
            """, (queue_id,))
        conn.commit()
        conn.close()
