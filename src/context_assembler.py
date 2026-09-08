from typing import List, Dict, Any, Optional
from src.models import ContactProfile, MemoryItem, ReconstructedInteraction

class ContextAssembler:
    """
    Context Assembler following the exact TDS context hierarchy:
    SYSTEM RULES -> GLOBAL USER STYLE -> CONTACT RELATIONSHIP -> RELEVANT MEMORIES -> SIMILAR HISTORICAL INTERACTIONS -> RECENT CONVERSATION -> CURRENT MESSAGE
    """

    @staticmethod
    def build_system_prompt(
        global_style: Dict[str, Any],
        contact_profile: Optional[ContactProfile] = None
    ) -> str:
        prompt = (
            "SYSTEM RULES:\n"
            "You are a personal WhatsApp communication assistant speaking authentically on behalf of the user.\n"
            "Never state or announce that you are an AI unless explicitly requested.\n"
            "Keep replies natural, concise, and aligned with the user's habitual communication patterns.\n\n"
            "GLOBAL USER STYLE:\n"
        )

        code_switch = global_style.get("code_switch_ratio", 0.0)
        slangs = ", ".join(list(global_style.get("slang_words", {}).keys())[:5])
        emojis = " ".join(list(global_style.get("emoji_dist", {}).keys())[:5])

        prompt += f"- Code-Switching Rate: {code_switch}\n"
        prompt += f"- Frequent Slang / Terms: {slangs or 'None'}\n"
        prompt += f"- Frequent Emojis: {emojis or 'None'}\n"
        prompt += f"- Average Response Length: {global_style.get('avg_sentence_len', 5)} words\n\n"

        if contact_profile:
            prompt += "CONTACT RELATIONSHIP:\n"
            prompt += f"- Category: {contact_profile.relationship_category}\n"
            prompt += f"- Formality Score: {contact_profile.formality_score} (0.0=Casual, 1.0=Strictly Formal)\n"
            greetings = ", ".join(contact_profile.preferred_greetings)
            prompt += f"- Preferred Greetings/Terms: {greetings or 'Standard'}\n"
            prompt += f"- Target Emojis: {' '.join(contact_profile.top_emojis[:3])}\n\n"

        return prompt

    @staticmethod
    def build_turn_context(
        incoming_message: str,
        recent_history: List[str],
        memories: List[MemoryItem],
        similar_interactions: List[ReconstructedInteraction]
    ) -> str:
        turn_text = ""

        if memories:
            turn_text += "RELEVANT MEMORIES / FACTS:\n"
            for m in memories:
                turn_text += f"- [{m.memory_type.upper()}] {m.fact_summary}\n"
            turn_text += "\n"

        if similar_interactions:
            turn_text += "SIMILAR PAST INTERACTIONS:\n"
            for idx, inter in enumerate(similar_interactions, 1):
                turn_text += f"Example {idx}:\n"
                turn_text += f"  Incoming: {inter.incoming_message}\n"
                turn_text += f"  User Response: {inter.user_response}\n"
            turn_text += "\n"

        if recent_history:
            turn_text += "RECENT CONVERSATION:\n"
            for msg in recent_history:
                turn_text += f"{msg}\n"
            turn_text += "\n"

        turn_text += f"CURRENT INCOMING MESSAGE:\n{incoming_message}\n"

        return turn_text
