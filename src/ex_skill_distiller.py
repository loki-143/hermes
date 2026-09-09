import os
import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class ExSkillDistiller:
    """
    Distills raw WhatsApp chat exports into an executable Hermes/Claude Skill (lokesh-persona).
    Implements ex-skill methodology: Persona (5 layers) + Memories + Rules.
    """
    def __init__(self, raw_chat_path: str, user_name: str = "Loki", slug: str = "lokesh"):
        self.raw_chat_path = raw_chat_path
        self.user_name = user_name
        self.slug = slug
        self.output_dir = Path(f"/home/lokesh/.hermes/skills/{slug}-persona")

    def parse_chat(self) -> List[Dict[str, Any]]:
        with open(self.raw_chat_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        lines = text.splitlines()
        messages = []
        pattern = re.compile(
            r"^(?:\[?(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]?)\s*-\s*([^:]+):\s*(.*)$",
            re.IGNORECASE
        )
        
        for line in lines:
            match = pattern.match(line.strip())
            if match:
                dt_str, sender, msg_text = match.groups()
                sender_clean = sender.strip()
                messages.append({
                    "sender": sender_clean,
                    "text": msg_text.strip(),
                    "is_user": sender_clean.lower() == self.user_name.lower()
                })
        return messages

    def extract_persona_rules(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        user_msgs = [m for m in messages if m["is_user"]]
        total_words = sum(len(m["text"].split()) for m in user_msgs)
        avg_len = round(total_words / max(1, len(user_msgs)), 2)

        slangs = {}
        telugu_words = ["ra", "ledhu", "sare", "avuna", "enti", "chudu", "undhi", "em", "le", "rey", "bava", "mama", "machi"]
        for m in user_msgs:
            for word in m["text"].lower().split():
                clean_w = word.strip(".,!?~")
                if clean_w in telugu_words:
                    slangs[clean_w] = slangs.get(clean_w, 0) + 1

        emojis = {}
        for m in user_msgs:
            for char in m["text"]:
                if char in "🥲🫠🙂😭😂🤣😏😁🥺":
                    emojis[char] = emojis.get(char, 0) + 1

        sample_replies = [m["text"] for m in user_msgs if 3 <= len(m["text"]) <= 40][:15]

        return {
            "avg_length": avg_len,
            "top_slangs": sorted(slangs.items(), key=lambda x: x[1], reverse=True),
            "top_emojis": sorted(emojis.items(), key=lambda x: x[1], reverse=True),
            "total_user_msgs": len(user_msgs),
            "sample_replies": sample_replies
        }

    def generate_skill_files(self):
        messages = self.parse_chat()
        persona = self.extract_persona_rules(messages)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # SKILL.md siguiendo la especificación ex-skill 5-Layer Persona & Memories
        sample_lines = "\n".join([f'- "{r}"' for r in persona['sample_replies'][:10]])

        skill_content = f"""---
name: {self.slug}-persona
description: "Use when responding in {self.user_name}'s authentic WhatsApp style."
version: "1.0.0"
user-invocable: true
---

# {self.user_name} WhatsApp Persona Skill (`ex-skill` Architecture)

Distilled directly from {len(messages)} WhatsApp chat messages ({persona['total_user_msgs']} messages from {self.user_name}).

---

## PART A: SHARED MEMORIES & RECURRENT RITUALS

- **Key Relationship:** Close friend / peer (`Abhiii 😊`).
- **Common Shared Contexts:** Project discussions (Scholar Lens, InnoTribe, ResNeXt, GitHub repos), college/campus routines, sharing links & memes, daily check-ins ("fast ga rammey", "where are you").

---

## PART B: 5-LAYER PERSONA SPECIFICATION

### Layer 0: System Directives (Strict Boundaries)
1. **Always speak directly in 1st person as {self.user_name}.** Never break character or announce that you are an AI.
2. **Short response target:** Keep replies between 2 to 6 words by default ({persona['avg_length']} words average).

### Layer 1: Core Personality & Tone
- Casual, relaxed, slightly informal, helpful yet concise.
- Prefers quick one-liners over long formal paragraphs.

### Layer 2: Vernacular & Code-Switching Rules (Telugu + English)
- Naturally weave Telugu slang into conversational English:
  - Primary slang words: {', '.join([k for k, v in persona['top_slangs'][:8]])}
  - Casual sentence endings: `sare sare...`, `ok ok`, `avuna...`, `ledhu`

### Layer 3: Text & Formatting Habits
- **Lowercase preference:** Minimal capitalization in quick messages.
- **Punctuation:** Trailing periods (`...` or `....`) for pauses, quick question marks (`?`), rare exclamation marks.
- **Emoji frequency:** Primary emojis: {' '.join([k for k, v in persona['top_emojis'][:6]])}.

### Layer 4: Real Text Examples (Few-Shot Pattern)
{sample_lines}

---

## PART C: RUNTIME DISPATCH RULES

When receiving an incoming message:
1. **Layer 0 Check:** Is this consequential/high-risk (payments/passwords)? If so, ask user confirmation.
2. **Tone Check:** Apply Layer 2 & 3 (Telugu-English code switching, brief response length, emoji habits).
3. **Output:** Generate authentic response as {self.user_name}.
"""
        with open(self.output_dir / "SKILL.md", "w", encoding="utf-8") as f:
            f.write(skill_content)

        print(f"✅ Generated distilled ex-skill at {self.output_dir}/SKILL.md")

if __name__ == "__main__":
    distiller = ExSkillDistiller("/home/lokesh/projects/whatsapp-agent/data/raw/WhatsApp Chat with Abhiii 😊.txt", user_name="Loki", slug="lokesh")
    distiller.generate_skill_files()
