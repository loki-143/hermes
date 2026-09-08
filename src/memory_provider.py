import sqlite3
from typing import List, Optional
from datetime import datetime
from src.models import MemoryItem

class WhatsAppMemoryProvider:
    """
    Pluggable Memory Provider implementing fact/episodic memory storage & retrieval
    conforming to Hermes MemoryProvider ABC requirements.
    """
    def __init__(self, db_path: str = "whatsapp_agent.db"):
        self.db_path = db_path

    def add_memory(self, memory: MemoryItem):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO memories (
                memory_id, contact_id, memory_type, fact_summary, confidence,
                created_at, last_accessed, temporal_target, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.memory_id,
            memory.contact_id,
            memory.memory_type,
            memory.fact_summary,
            memory.confidence,
            memory.created_at or datetime.now(),
            memory.last_accessed or datetime.now(),
            memory.temporal_target,
            1 if memory.is_active else 0
        ))
        conn.commit()
        conn.close()

    def prefetch(self, contact_id: Optional[str] = None, limit: int = 5) -> List[MemoryItem]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if contact_id:
            cur.execute("""
                SELECT memory_id, contact_id, memory_type, fact_summary, confidence,
                       created_at, last_accessed, temporal_target, is_active
                FROM memories
                WHERE (contact_id = ? OR contact_id IS NULL) AND is_active = 1
                ORDER BY created_at DESC LIMIT ?
            """, (contact_id, limit))
        else:
            cur.execute("""
                SELECT memory_id, contact_id, memory_type, fact_summary, confidence,
                       created_at, last_accessed, temporal_target, is_active
                FROM memories
                WHERE is_active = 1
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()

        memories = []
        for r in rows:
            memories.append(MemoryItem(
                memory_id=r[0],
                contact_id=r[1],
                memory_type=r[2],
                fact_summary=r[3],
                confidence=r[4],
                created_at=datetime.fromisoformat(r[5]) if isinstance(r[5], str) else r[5],
                last_accessed=datetime.fromisoformat(r[6]) if isinstance(r[6], str) else r[6],
                temporal_target=datetime.fromisoformat(r[7]) if (r[7] and isinstance(r[7], str)) else r[7],
                is_active=bool(r[8])
            ))
        return memories
