from datetime import datetime
from src.models import ReconstructedInteraction
from src.interaction_rag import InteractionRAG
from src.approval_queue import ApprovalItem

class ContinuousLearningPipeline:
    """
    Subsystem for processing user human edits and new active turns,
    updating interaction RAG, memory candidates, and edit delta feedback.
    """
    def __init__(self, rag_engine: InteractionRAG):
        self.rag_engine = rag_engine

    def record_human_edit_delta(self, item: ApprovalItem, final_user_text: str):
        """
        Record the difference between candidate response and final user edit.
        Indexes the final approved user text into the interaction RAG store.
        """
        interaction = ReconstructedInteraction(
            interaction_id=f"learned_{item.queue_id}",
            contact_id=item.contact_id,
            incoming_message=item.incoming_message,
            context_history=[],
            user_response=final_user_text,
            relationship_category="learned_feedback",
            timestamp=datetime.now()
        )
        self.rag_engine.index_interaction(interaction)
