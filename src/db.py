import sqlite3

def init_db(db_path: str = "whatsapp_agent.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Contacts & Relationship Profiles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        contact_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        relationship_category TEXT DEFAULT 'acquaintance',
        formality_score REAL DEFAULT 0.5,
        preferred_greetings TEXT,
        code_switching_rate REAL DEFAULT 0.0,
        emoji_frequency REAL DEFAULT 0.0,
        top_emojis TEXT,
        avg_response_length REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Normalized Messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS normalized_messages (
        message_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        message_text TEXT NOT NULL,
        is_user BOOLEAN NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        reply_to_id TEXT,
        metadata JSON
    );
    """)

    # Reconstructed Interactions (Two-Sided Learning)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reconstructed_interactions (
        interaction_id TEXT PRIMARY KEY,
        contact_id TEXT NOT NULL,
        incoming_message TEXT NOT NULL,
        context_history JSON,
        user_response TEXT NOT NULL,
        relationship_category TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        FOREIGN KEY (contact_id) REFERENCES contacts (contact_id)
    );
    """)

    # Fact & Episode Memory Store
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        memory_id TEXT PRIMARY KEY,
        contact_id TEXT,
        memory_type TEXT NOT NULL, -- 'semantic', 'episodic', 'relationship', 'temporal', 'preference'
        fact_summary TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        temporal_target TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (contact_id) REFERENCES contacts (contact_id)
    );
    """)

    # Global Style Metrics
    cur.execute("""
    CREATE TABLE IF NOT EXISTS global_style (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        vocab_freq JSON,
        slang_words JSON,
        code_switch_ratio REAL DEFAULT 0.0,
        avg_sentence_len REAL DEFAULT 0.0,
        emoji_dist JSON,
        punctuation_style JSON,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Full-Text Search (FTS5) for Interaction Retrieval
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS interactions_fts USING fts5(
        interaction_id UNINDEXED,
        contact_id,
        incoming_message,
        user_response,
        relationship_category
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
