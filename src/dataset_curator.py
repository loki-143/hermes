from typing import List, Dict, Any
from src.models import ReconstructedInteraction
from src.context_assembler import ContextAssembler

def build_fine_tuning_dataset(
    interactions: List[ReconstructedInteraction],
    global_style: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Format high-quality reconstructed interactions into structured SFT (Supervised Fine-Tuning)
    dataset items, avoiding raw chat export dumps.
    """
    dataset = []
    for inter in interactions:
        system_prompt = ContextAssembler.build_system_prompt(global_style)
        turn_context = ContextAssembler.build_turn_context(
            incoming_message=inter.incoming_message,
            recent_history=inter.context_history,
            memories=[],
            similar_interactions=[]
        )
        
        dataset.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": turn_context},
                {"role": "assistant", "content": inter.user_response}
            ],
            "metadata": {
                "contact_id": inter.contact_id,
                "relationship_category": inter.relationship_category,
                "timestamp": str(inter.timestamp)
            }
        })
    return dataset
