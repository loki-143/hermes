import sqlite3
from typing import List, Optional
from src.models import ReconstructedInteraction

class InteractionRAG:
    """
    RAG Subsystem for indexing and retrieving 2-sided historical interaction tuples
    (incoming contact message -> user response) using SQLite FTS5.
    """
    def __init__(self, db_path: str = "whatsapp_agent.db"):
        self.db_path = db_path

    def index_interaction(self, interaction: ReconstructedInteraction):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Save to main table
        cur.execute("""
            INSERT OR REPLACE INTO reconstructed_interactions (
                interaction_id, contact_id, incoming_message, context_history,
                user_response, relationship_category, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.interaction_id,
            interaction.contact_id,
            interaction.incoming_message,
            str(interaction.context_history),
            interaction.user_response,
            interaction.relationship_category,
            interaction.timestamp
        ))

        # Index in FTS5
        cur.execute("""
            INSERT OR REPLACE INTO interactions_fts (
                interaction_id, contact_id, incoming_message, user_response, relationship_category
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            interaction.interaction_id,
            interaction.contact_id,
            interaction.incoming_message,
            interaction.user_response,
            interaction.relationship_category
        ))

        conn.commit()
        conn.close()

    def search_similar_interactions(
        self,
        query_text: str,
        contact_id: Optional[str] = None,
        limit: int = 3
    ) -> List[ReconstructedInteraction]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Sanitize query for FTS5
        clean_query = "".join(c for c in query_text if c.isalnum() or c.isspace()).strip()
        if not clean_query:
            conn.close()
            return []

        fts_query = " OR ".join(clean_query.split())

        if contact_id:
            cur.execute("""
                SELECT i.interaction_id, i.contact_id, i.incoming_message, i.context_history,
                       i.user_response, i.relationship_category, i.timestamp
                FROM interactions_fts f
                JOIN reconstructed_interactions i ON f.interaction_id = i.interaction_id
                WHERE interactions_fts MATCH ? AND i.contact_id = ?
                LIMIT ?
            """, (fts_query, contact_id, limit))
        else:
            cur.execute("""
                SELECT i.interaction_id, i.contact_id, i.incoming_message, i.context_history,
                       i.user_response, i.relationship_category, i.timestamp
                FROM interactions_fts f
                JOIN reconstructed_interactions i ON f.interaction_id = i.interaction_id
                WHERE interactions_fts MATCH ?
                LIMIT ?
            """, (fts_query, limit))

        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append(ReconstructedInteraction(
                interaction_id=r[0],
                contact_id=r[1],
                incoming_message=r[2],
                context_history=eval(r[3]) if r[3] and r[3].startswith("[") else [],
                user_response=r[4],
                relationship_category=r[5],
                timestamp=r[6]
            ))
        return results
