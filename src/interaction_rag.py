import sqlite3
import re
from typing import List, Optional
from src.models import ReconstructedInteraction

def tokenize(text: str) -> set:
    words = re.findall(r'\b\w+\b', text.lower())
    return set(words)

class InteractionRAG:
    """
    RAG Subsystem for indexing and retrieving 2-sided historical interaction tuples
    (incoming contact message -> user response) using token-overlap similarity scoring.
    """
    def __init__(self, db_path: str = "live_whatsapp.db"):
        self.db_path = db_path

    def index_interaction(self, interaction: ReconstructedInteraction):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
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
        limit: int = 5
    ) -> List[ReconstructedInteraction]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        clean_query = query_text.strip().lower()
        if not clean_query:
            conn.close()
            return []

        query_tokens = tokenize(clean_query)

        # Step 1: Substring match in SQL
        like_pattern = f"%{clean_query}%"
        if contact_id:
            cur.execute("""
                SELECT interaction_id, contact_id, incoming_message, context_history,
                       user_response, relationship_category, timestamp
                FROM reconstructed_interactions
                WHERE contact_id = ? AND LOWER(incoming_message) LIKE ?
                ORDER BY length(incoming_message) ASC
                LIMIT ?
            """, (contact_id, like_pattern, limit))
        else:
            cur.execute("""
                SELECT interaction_id, contact_id, incoming_message, context_history,
                       user_response, relationship_category, timestamp
                FROM reconstructed_interactions
                WHERE LOWER(incoming_message) LIKE ?
                ORDER BY length(incoming_message) ASC
                LIMIT ?
            """, (like_pattern, limit))

        exact_rows = cur.fetchall()
        
        # Step 2: Token-Overlap Scoring over candidate pool
        candidate_rows = list(exact_rows)
        if len(candidate_rows) < limit * 3:
            # Query candidate pool matching any token
            token_likes = [f"%{t}%" for t in query_tokens if len(t) >= 2]
            if token_likes:
                kw_conditions = " OR ".join(["LOWER(incoming_message) LIKE ?" for _ in token_likes])
                if contact_id:
                    cur.execute(f"""
                        SELECT interaction_id, contact_id, incoming_message, context_history,
                               user_response, relationship_category, timestamp
                        FROM reconstructed_interactions
                        WHERE contact_id = ? AND ({kw_conditions})
                        LIMIT 200
                    """, [contact_id] + token_likes)
                else:
                    cur.execute(f"""
                        SELECT interaction_id, contact_id, incoming_message, context_history,
                               user_response, relationship_category, timestamp
                        FROM reconstructed_interactions
                        WHERE {kw_conditions}
                        LIMIT 200
                    """, token_likes)
                
                extra_rows = cur.fetchall()
                seen_ids = set(r[0] for r in candidate_rows)
                for r in extra_rows:
                    if r[0] not in seen_ids:
                        candidate_rows.append(r)

        conn.close()

        # Score candidates based on Jaccard / Token Overlap
        scored = []
        for r in candidate_rows:
            inc_tokens = tokenize(r[2])
            overlap = len(query_tokens.intersection(inc_tokens))
            union = len(query_tokens.union(inc_tokens)) or 1
            jaccard = overlap / union
            scored.append((jaccard, overlap, r))

        # Sort by overlap score descending, then by length ascending
        scored.sort(key=lambda x: (x[0], x[1], -len(x[2][2])), reverse=True)

        results = []
        for _, _, r in scored[:limit]:
            results.append(ReconstructedInteraction(
                interaction_id=r[0], contact_id=r[1], incoming_message=r[2],
                context_history=eval(r[3]) if r[3] and r[3].startswith("[") else [],
                user_response=r[4], relationship_category=r[5], timestamp=r[6]
            ))

        return results
