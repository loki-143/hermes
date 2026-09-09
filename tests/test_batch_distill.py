import zipfile
import pytest
from pathlib import Path
from src.batch_distill import BatchWhatsAppDistiller

def test_batch_distiller_zip(tmp_path):
    zip_path = tmp_path / "all_chats.zip"
    db_path = str(tmp_path / "batch_test.db")
    skills_dir = tmp_path / "skills"

    # Create dummy chat 1
    chat1_content = """24/06/2026, 10:00 - Rahul: Hi bro
24/06/2026, 10:01 - Loki: Rey cheppu ra
24/06/2026, 10:02 - Rahul: Em chesthunnav?
24/06/2026, 10:03 - Loki: Ntng ra
"""

    # Create dummy chat 2
    chat2_content = """24/06/2026, 11:00 - Hema: Hi Lokesh
24/06/2026, 11:01 - Loki: Ha Hema cheppu
24/06/2026, 11:02 - Hema: Notes unnaaya?
24/06/2026, 11:03 - Loki: Ha pamputha
"""

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("WhatsApp Chat with Rahul.txt", chat1_content)
        zf.writestr("WhatsApp Chat with Hema.txt", chat2_content)

    distiller = BatchWhatsAppDistiller(target_dir_or_zip=str(zip_path), db_path=db_path, user_name="Loki")
    results = distiller.process_all()

    assert len(results) == 2
    contact_names = [r["contact_name"] for r in results]
    assert "Rahul" in contact_names
    assert "Hema" in contact_names
    for r in results:
        assert r["status"] == "SUCCESS"
        assert r["indexed_interactions"] > 0
