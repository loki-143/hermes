import sqlite3
import pytest
from pathlib import Path
from src.sqlite_msgstore_distiller import SQLiteMsgstoreDistiller
from src.interaction_rag import InteractionRAG

def create_mock_msgstore_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create WhatsApp Android msgstore schema subset
    cur.execute("""
        CREATE TABLE jid (
            _id INTEGER PRIMARY KEY,
            user TEXT,
            server TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE chat (
            _id INTEGER PRIMARY KEY,
            jid_row_id INTEGER
        );
    """)
    cur.execute("""
        CREATE TABLE message (
            _id INTEGER PRIMARY KEY,
            chat_row_id INTEGER,
            from_me INTEGER,
            text_data TEXT,
            timestamp INTEGER
        );
    """)

    # Insert mock contact: 919876543210
    cur.execute("INSERT INTO jid (_id, user, server) VALUES (1, '919876543210', 's.whatsapp.net');")
    cur.execute("INSERT INTO chat (_id, jid_row_id) VALUES (1, 1);")

    # Insert 16 messages (alternating contact and user) to exceed min_messages=15 threshold
    base_ts = 1700000000000
    for i in range(16):
        from_me = 1 if i % 2 == 1 else 0
        text = f"User message {i} sare ra" if from_me else f"Contact question {i} bro"
        ts = base_ts + (i * 60000)
        cur.execute(
            "INSERT INTO message (_id, chat_row_id, from_me, text_data, timestamp) VALUES (?, 1, ?, ?, ?)",
            (i + 1, from_me, text, ts)
        )
    
    conn.commit()
    conn.close()

def test_sqlite_msgstore_distiller_extraction_and_indexing(tmp_path, monkeypatch):
    msgstore_db = tmp_path / "mock_msgstore.db"
    rag_db = tmp_path / "mock_rag.db"
    
    create_mock_msgstore_db(msgstore_db)

    # Monkeypatch output_dir of PersonSpecificExSkillDistiller to avoid writing into ~/.hermes/skills during test
    temp_skills_dir = tmp_path / "skills"
    temp_skills_dir.mkdir()
    
    distiller = SQLiteMsgstoreDistiller(
        db_path=str(msgstore_db),
        target_rag_db=str(rag_db),
        user_name="Loki"
    )
    distiller.raw_export_dir = tmp_path / "msgstore_extracted"
    distiller.raw_export_dir.mkdir(parents=True, exist_ok=True)

    def mock_init(self_inner, raw_chat_path, contact_name, user_name="Loki"):
        self_inner.raw_chat_path = raw_chat_path
        self_inner.contact_name = contact_name
        self_inner.user_name = user_name
        self_inner.contact_slug = "919876543210"
        self_inner.skill_name = "lokesh-919876543210-persona"
        self_inner.output_dir = temp_skills_dir / self_inner.skill_name

    monkeypatch.setattr("src.person_skill_distiller.PersonSpecificExSkillDistiller.__init__", mock_init)

    # Execute extraction
    extracted = distiller.extract_chats(min_messages=15)
    assert len(extracted) == 1
    assert extracted[0]["phone_number"] == "919876543210"
    assert extracted[0]["raw_count"] == 16
    assert len(extracted[0]["messages"]) == 16

    # Execute full distillation & indexing
    results = distiller.distill_all(min_messages=15)
    assert len(results) == 1
    assert results[0]["status"] == "SUCCESS"
    assert results[0]["contact_id"] == "919876543210"
    assert results[0]["indexed_interactions"] > 0

    # Verify interaction RAG indexed the tuples
    rag = InteractionRAG(str(rag_db))
    searched = rag.search_similar_interactions("bro", contact_id="919876543210", limit=5)
    assert len(searched) > 0
