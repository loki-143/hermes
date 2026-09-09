import os
import re
import zipfile
from pathlib import Path
from typing import List, Dict, Any
from src.db import init_db
from src.ingestion import parse_whatsapp_chat, reconstruct_interactions
from src.interaction_rag import InteractionRAG
from src.person_skill_distiller import PersonSpecificExSkillDistiller

class BatchWhatsAppDistiller:
    """
    Bulk Distiller for WhatsApp Chat Exports.
    Processes a directory of .txt files or a single .zip archive containing multiple chat exports.
    Automatically:
      1. Parses each contact's chat text.
      2. Distills a dedicated person-specific skill (lokesh-{contact}-persona).
      3. Indexes interaction tuples into SQLite RAG (live_whatsapp.db).
    """
    def __init__(self, target_dir_or_zip: str, db_path: str = "live_whatsapp.db", user_name: str = "Loki"):
        self.target_path = Path(target_dir_or_zip)
        self.db_path = db_path
        self.user_name = user_name
        self.raw_dir = Path("data/raw/bulk_extracted")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        init_db(db_path)
        self.rag = InteractionRAG(db_path)

    def extract_materials(self) -> List[Path]:
        txt_files = []
        if self.target_path.is_file() and self.target_path.suffix == ".zip":
            with zipfile.ZipFile(self.target_path, "r") as zip_ref:
                zip_ref.extractall(self.raw_dir)
            txt_files = list(self.raw_dir.glob("*.txt"))
        elif self.target_path.is_dir():
            txt_files = list(self.target_path.glob("*.txt"))
        return txt_files

    def _extract_contact_name(self, filename: str) -> str:
        name = filename.replace("WhatsApp Chat with ", "").replace(".txt", "").strip()
        name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip()
        return name or "UnknownContact"

    def process_all(self) -> List[Dict[str, Any]]:
        txt_files = self.extract_materials()
        results = []

        print(f"📦 Found {len(txt_files)} chat export files to process...")

        for file_path in txt_files:
            contact_name = self._extract_contact_name(file_path.name)
            print(f"\n🔄 Processing contact: {contact_name} ({file_path.name})...")

            try:
                # 1. Distill Skill
                distiller = PersonSpecificExSkillDistiller(
                    raw_chat_path=str(file_path),
                    contact_name=contact_name,
                    user_name=self.user_name
                )
                skill_name = distiller.generate_person_skill()

                # 2. Ingest into RAG
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                msgs = parse_whatsapp_chat(text, conversation_id=f"conv_{contact_name}", user_name=self.user_name)
                interactions = reconstruct_interactions(msgs, contact_id=contact_name)

                # Batch index for performance
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
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
                conn.close()

                results.append({
                    "contact_name": contact_name,
                    "skill_name": skill_name,
                    "parsed_messages": len(msgs),
                    "indexed_interactions": len(interactions),
                    "status": "SUCCESS"
                })
                print(f"✅ Finished {contact_name}: Skill '{skill_name}', {len(interactions)} interaction pairs indexed.")

            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}")
                results.append({
                    "contact_name": contact_name,
                    "file": file_path.name,
                    "status": "ERROR",
                    "error": str(e)
                })

        return results

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    batch = BatchWhatsAppDistiller(target_dir_or_zip=target)
    summary = batch.process_all()
    print("\n=== BULK DISTILLATION COMPLETE ===")
    for s in summary:
        print(s)
