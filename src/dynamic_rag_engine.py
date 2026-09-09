import sqlite3
from typing import List, Dict, Any, Optional
from src.interaction_rag import InteractionRAG
from src.context_assembler import ContextAssembler
from src.models import ReconstructedInteraction

class DynamicRAGEngine:
    """
    Dynamic Few-Shot RAG Engine:
    Retrieves exact historical interaction pairs from SQLite RAG database
    at turn time and injects them as few-shot examples into the LLM prompt.
    Prevents LLM from falling back to generic AI persona summaries.
    """
    def __init__(self, db_path: str = "live_whatsapp.db"):
        self.db_path = db_path
        self.rag = InteractionRAG(db_path)

    def assemble_fewshot_prompt(
        self,
        incoming_message: str,
        contact_id: str,
        recent_history: Optional[List[str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        # 1. Retrieve top matching historical interaction pairs for this specific contact
        matches = self.rag.search_similar_interactions(
            query_text=incoming_message,
            contact_id=contact_id,
            limit=limit
        )

        # If no direct query match, retrieve recent historical pairs for contact grounding
        if not matches:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT interaction_id, contact_id, incoming_message, context_history,
                       user_response, relationship_category, timestamp
                FROM reconstructed_interactions
                WHERE contact_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (contact_id, limit))
            rows = cur.fetchall()
            conn.close()
            for r in rows:
                matches.append(ReconstructedInteraction(
                    interaction_id=r[0], contact_id=r[1], incoming_message=r[2],
                    context_history=eval(r[3]) if r[3] and r[3].startswith("[") else [],
                    user_response=r[4], relationship_category=r[5], timestamp=r[6]
                ))

        # 2. Build Few-Shot System Instruction
        fewshot_block = f"EXACT HISTORICAL FEW-SHOT EXAMPLES (WhatsApp chat logs with {contact_id}):\n"
        for idx, m in enumerate(matches, 1):
            fewshot_block += f"Example {idx}:\n"
            fewshot_block += f"  Incoming ({contact_id}): \"{m.incoming_message}\"\n"
            fewshot_block += f"  User Reply (Loki): \"{m.user_response}\"\n"

        system_instruction = f"""SYSTEM DIRECTIVE:
You are Loki responding on WhatsApp to {contact_id}.
STRICT RULE: You MUST mimic the exact response style, word count (typically 1-4 words), vernacular Telugu-English slang, trailing periods, and tone demonstrated in the historical examples below. Never invent artificial multi-clause AI sentences or polite filler.

{fewshot_block}
"""

        user_prompt = ""
        if recent_history:
            user_prompt += "RECENT CONVERSATION:\n"
            for h in recent_history:
                user_prompt += f"{h}\n"
            user_prompt += "\n"

        user_prompt += f"INCOMING MESSAGE ({contact_id}):\n\"{incoming_message}\"\n\nGenerate Loki's exact response:"

        return {
            "system_instruction": system_instruction,
            "user_prompt": user_prompt,
            "matched_interactions": [m.model_dump() for m in matches]
        }
