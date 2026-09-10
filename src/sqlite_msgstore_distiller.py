import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any
from src.db import init_db
from src.ingestion import NormalizedMessage, reconstruct_interactions
from src.interaction_rag import InteractionRAG
from src.person_skill_distiller import PersonSpecificExSkillDistiller

class SQLiteMsgstoreDistiller:
    """
    Direct Distiller for Unencrypted Android WhatsApp SQLite Databases (msgstore.db).
    Reads 1-on-1 chats directly from message + chat + jid tables.
    Distills person-specific ex-skills (lokesh-{contact}-persona) and indexes
    reconstructed interaction tuples directly into SQLite RAG (live_whatsapp.db).
    """
    def __init__(self, db_path: str = "/home/lokesh/data/msgstore.db", target_rag_db: str = "live_whatsapp.db", user_name: str = "Loki"):
        self.msgstore_path = db_path
        self.target_rag_db = target_rag_db
        self.user_name = user_name
        self.raw_export_dir = Path("data/raw/msgstore_extracted")
        self.raw_export_dir.mkdir(parents=True, exist_ok=True)
        init_db(target_rag_db)
        self.rag = InteractionRAG(target_rag_db)

    def extract_chats(self, min_messages: int = 15) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.msgstore_path)
        cur = conn.cursor()

        # Query all direct 1-on-1 chats with more than min_messages
        query_chats = """
            SELECT c._id, j.user, COUNT(m._id) as msg_count
            FROM chat c
            JOIN jid j ON c.jid_row_id = j._id
            JOIN message m ON m.chat_row_id = c._id
            WHERE j.server = 's.whatsapp.net'
            GROUP BY c._id
            HAVING msg_count >= ?
            ORDER BY msg_count DESC
        """
        cur.execute(query_chats, (min_messages,))
        chats = cur.fetchall()
        
        extracted_info = []

        for chat_id, phone_number, count in chats:
            # Query messages for this chat
            query_msgs = """
                SELECT m._id, m.from_me, m.text_data, m.timestamp
                FROM message m
                WHERE m.chat_row_id = ? AND m.text_data IS NOT NULL AND m.text_data != ''
                ORDER BY m.timestamp ASC
            """
            cur.execute(query_msgs, (chat_id,))
            rows = cur.fetchall()

            if not rows:
                continue

            # Convert to standard WhatsApp export text format
            lines = []
            normalized_msgs = []

            for msg_id, from_me, text_data, ts in rows:
                # Convert epoch millisecond timestamp to standard format
                dt = datetime.datetime.fromtimestamp(ts / 1000.0)
                date_str = dt.strftime("%d/%m/%Y, %H:%M")
                sender = self.user_name if from_me == 1 else phone_number
                
                # Clean newlines inside single message
                clean_text = text_data.replace('\n', ' ')
                lines.append(f"{date_str} - {sender}: {clean_text}")

                normalized_msgs.append(NormalizedMessage(
                    message_id=str(msg_id),
                    conversation_id=f"conv_{phone_number}",
                    sender_id=sender,
                    sender_name=sender,
                    message_text=text_data,
                    is_user=(from_me == 1),
                    timestamp=dt
                ))

            # Save export text file
            txt_file = self.raw_export_dir / f"WhatsApp Chat with {phone_number}.txt"
            txt_file.write_text("\n".join(lines), encoding="utf-8")

            extracted_info.append({
                "chat_id": chat_id,
                "phone_number": phone_number,
                "txt_file": str(txt_file),
                "messages": normalized_msgs,
                "raw_count": count
            })

        conn.close()
        return extracted_info

    def distill_all(self, min_messages: int = 15) -> List[Dict[str, Any]]:
        extracted = self.extract_chats(min_messages=min_messages)
        print(f"📦 Extracted {len(extracted)} direct 1-on-1 contact chats from SQLite database...")

        results = []
        conn = sqlite3.connect(self.target_rag_db)
        cur = conn.cursor()

        for chat in extracted:
            phone_number = chat["phone_number"]
            txt_file = chat["txt_file"]
            msgs = chat["messages"]

            print(f"\n🔄 Distilling skill & indexing for contact: {phone_number} ({len(msgs)} text messages)...")

            try:
                # 1. Distill Skill
                distiller = PersonSpecificExSkillDistiller(
                    raw_chat_path=txt_file,
                    contact_name=phone_number,
                    user_name=self.user_name
                )
                skill_name = distiller.generate_person_skill()

                # 2. Reconstruct 2-sided interactions
                interactions = reconstruct_interactions(msgs, contact_id=phone_number)

                # 3. Batch Index into RAG
                cur.executemany("""
                    INSERT OR REPLACE INTO reconstructed_interactions (
                        interaction_id, contact_id, incoming_message, context_history,
                        user_response, relationship_category, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [(
                    inter.interaction_id, inter.contact_id, inter.incoming_message,
                    str(inter.context_history), inter.user_response,
                    inter.relationship_category, inter.timestamp
                ) for inter in interactions])

                cur.executemany("""
                    INSERT OR REPLACE INTO interactions_fts (
                        interaction_id, contact_id, incoming_message, user_response, relationship_category
                    ) VALUES (?, ?, ?, ?, ?)
                """, [(
                    inter.interaction_id, inter.contact_id, inter.incoming_message,
                    inter.user_response, inter.relationship_category
                ) for inter in interactions])

                conn.commit()

                results.append({
                    "contact_id": phone_number,
                    "skill_name": skill_name,
                    "parsed_messages": len(msgs),
                    "indexed_interactions": len(interactions),
                    "status": "SUCCESS"
                })
                print(f"✅ Finished {phone_number}: Skill '{skill_name}', {len(interactions)} interaction pairs indexed into RAG.")

            except Exception as e:
                print(f"❌ Error distilling {phone_number}: {e}")
                results.append({
                    "contact_id": phone_number,
                    "status": "ERROR",
                    "error": str(e)
                })

        conn.close()
        return results

if __name__ == "__main__":
    distiller = SQLiteMsgstoreDistiller()
    results = distiller.distill_all(min_messages=15)
    print("\n=== BULK SQLITE DISTILLATION COMPLETE ===")
    for r in results:
        print(r)
