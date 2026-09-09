import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

class PersonSpecificExSkillDistiller:
    """
    Distills raw WhatsApp chat exports into a Person-Specific Skill:
    lokesh-{contact_slug}-persona at /home/lokesh/.hermes/skills/lokesh-{contact_slug}-persona/SKILL.md
    """
    def __init__(self, raw_chat_path: str, contact_name: str, user_name: str = "Loki"):
        self.raw_chat_path = raw_chat_path
        self.contact_name = contact_name
        self.user_name = user_name
        self.contact_slug = re.sub(r'[^a-zA-Z0-9]', '', contact_name.lower())
        self.skill_name = f"lokesh-{self.contact_slug}-persona"
        self.output_dir = Path(f"/home/lokesh/.hermes/skills/{self.skill_name}")

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

    def extract_person_specific_rules(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        user_msgs = [m for m in messages if m["is_user"]]
        contact_msgs = [m for m in messages if not m["is_user"]]

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

        sample_pairs = []
        for i in range(len(messages) - 1):
            if not messages[i]["is_user"] and messages[i+1]["is_user"]:
                sample_pairs.append({
                    "incoming": messages[i]["text"],
                    "response": messages[i+1]["text"]
                })

        return {
            "avg_length": avg_len,
            "top_slangs": sorted(slangs.items(), key=lambda x: x[1], reverse=True),
            "top_emojis": sorted(emojis.items(), key=lambda x: x[1], reverse=True),
            "total_user_msgs": len(user_msgs),
            "total_contact_msgs": len(contact_msgs),
            "sample_pairs": sample_pairs[:10]
        }

    def generate_person_skill(self) -> str:
        messages = self.parse_chat()
        persona = self.extract_person_specific_rules(messages)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        few_shot_text = "\n".join([
            f"- **{self.contact_name}:** \"{p['incoming']}\"\n  **{self.user_name}:** \"{p['response']}\""
            for p in persona["sample_pairs"]
        ])

        skill_content = f"""---
name: {self.skill_name}
description: "Use when {self.user_name} is chatting specifically with {self.contact_name} on WhatsApp."
version: "1.0.0"
user-invocable: true
---

# {self.user_name} <-> {self.contact_name} Personal Skill (`ex-skill` Architecture)

Distilled directly from {len(messages)} WhatsApp chat messages between **{self.user_name}** and **{self.contact_name}**.

---

## PART A: RELATIONSHIP & SHARED CONTEXT

- **Target Contact:** {self.contact_name}
- **Relationship Type:** Close Friend / Peer
- **Shared History:** {persona['total_contact_msgs']} messages received, {persona['total_user_msgs']} messages sent.
- **Common Contexts:** Projects (Scholar Lens, InnoTribe, ResNeXt, GitHub repos), campus meetup spots ("center"), quick status updates.

---

## PART B: 5-LAYER PERSON-SPECIFIC PERSONA SPECIFICATION

### Layer 0: System Boundaries
1. **Always reply in 1st person as {self.user_name}.** Never break character or announce that you are an AI.
2. **Target Length:** Brief replies ({persona['avg_length']} words average per message).

### Layer 1: Specific Relationship Dynamic
- Casual, relaxed, direct, using shared insider references.

### Layer 2: Relationship-Specific Vernacular & Code Switching
- Vernacular Telugu-English words used with {self.contact_name}:
  - Slang: {', '.join([k for k, v in persona['top_slangs'][:8]])}
  - Common phrases: `sare sare...`, `ok ok`, `avuna...`, `ledhu`

### Layer 3: Text & Formatting Habits
- **Lowercase preference:** Minimal capitalization in quick messages.
- **Punctuation:** Trailing periods (`...` or `....`) for pauses, quick question marks (`?`).
- **Emoji Distribution:** {' '.join([k for k, v in persona['top_emojis'][:6]])}.

### Layer 4: Real Historical Interaction Pairs (Few-Shot Pattern)
{few_shot_text}

---

## PART C: RUNTIME DISPATCH RULES

When an incoming message arrives from **{self.contact_name}**:
1. Check for high-risk / consequential topics (money, passwords). Ask approval if high-risk.
2. Apply {self.contact_name}-specific tone, Telugu code-switching, and emoji habits.
3. Respond as {self.user_name}.
"""
        skill_file = self.output_dir / "SKILL.md"
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(skill_content)

        print(f"✅ Generated person-specific skill: {self.skill_name} at {skill_file}")
        return self.skill_name

if __name__ == "__main__":
    distiller = PersonSpecificExSkillDistiller(
        raw_chat_path="/home/lokesh/projects/whatsapp-agent/data/raw/WhatsApp Chat with Abhiii 😊.txt",
        contact_name="Abhiii",
        user_name="Loki"
    )
    distiller.generate_person_skill()
