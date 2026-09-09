import os
import tempfile
import pytest
from pathlib import Path
from src.ex_skill_distiller import ExSkillDistiller
from src.person_skill_distiller import PersonSpecificExSkillDistiller

SAMPLE_CHAT = """13/03/25, 11:00 am - Abhiii: Bro fast gaa rammey center ki
13/03/25, 11:01 am - Loki: Ostha ra 5 mins lo 😂
13/03/25, 11:02 am - Abhiii: Sare jaldi ra
13/03/25, 11:03 am - Loki: ok ok ledhu delay avvakunda ostha
"""

def test_ex_skill_distiller(tmp_path):
    chat_file = tmp_path / "sample_chat.txt"
    chat_file.write_text(SAMPLE_CHAT, encoding="utf-8")

    distiller = ExSkillDistiller(raw_chat_path=str(chat_file), user_name="Loki", slug="test-loki")
    distiller.output_dir = tmp_path / "skills" / "test-loki-persona"

    messages = distiller.parse_chat()
    assert len(messages) == 4
    assert messages[1]["is_user"] is True
    assert messages[1]["sender"] == "Loki"

    persona = distiller.extract_persona_rules(messages)
    assert persona["total_user_msgs"] == 2
    assert ("ra", 1) in persona["top_slangs"]
    assert ("😂", 1) in persona["top_emojis"]

    distiller.generate_skill_files()
    skill_md = distiller.output_dir / "SKILL.md"
    assert skill_md.exists()
    content = skill_md.read_text(encoding="utf-8")
    assert "name: test-loki-persona" in content
    assert "Loki" in content

def test_person_skill_distiller(tmp_path):
    chat_file = tmp_path / "sample_chat.txt"
    chat_file.write_text(SAMPLE_CHAT, encoding="utf-8")

    distiller = PersonSpecificExSkillDistiller(
        raw_chat_path=str(chat_file),
        contact_name="Abhiii",
        user_name="Loki"
    )
    distiller.output_dir = tmp_path / "skills" / "lokesh-abhiii-persona"

    messages = distiller.parse_chat()
    assert len(messages) == 4

    rules = distiller.extract_person_specific_rules(messages)
    assert rules["total_user_msgs"] == 2
    assert rules["total_contact_msgs"] == 2
    assert len(rules["sample_pairs"]) == 2

    skill_name = distiller.generate_person_skill()
    assert skill_name == "lokesh-abhiii-persona"
    skill_md = distiller.output_dir / "SKILL.md"
    assert skill_md.exists()
    content = skill_md.read_text(encoding="utf-8")
    assert "Abhiii" in content
    assert "Ostha ra 5 mins lo 😂" in content
