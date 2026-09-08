import pytest
import sqlite3
from src.db import init_db
from src.models import MemoryItem
from src.memory_provider import WhatsAppMemoryProvider
from datetime import datetime

@pytest.fixture
def memory_provider(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    init_db(db_file)
    return WhatsAppMemoryProvider(db_path=db_file)

def test_add_and_prefetch_memory(memory_provider):
    item1 = MemoryItem(
        memory_id="mem_1",
        contact_id="rahul_123",
        memory_type="episodic",
        fact_summary="Rahul has a job interview on Monday.",
        confidence=0.95
    )
    item2 = MemoryItem(
        memory_id="mem_2",
        contact_id="prof_456",
        memory_type="semantic",
        fact_summary="Prof Smith expects lab report by 5 PM.",
        confidence=1.0
    )
    
    memory_provider.add_memory(item1)
    memory_provider.add_memory(item2)
    
    rahul_memories = memory_provider.prefetch(contact_id="rahul_123")
    assert len(rahul_memories) == 1
    assert rahul_memories[0].memory_id == "mem_1"
    assert "interview" in rahul_memories[0].fact_summary

    all_memories = memory_provider.prefetch(contact_id=None, limit=10)
    assert len(all_memories) == 2
