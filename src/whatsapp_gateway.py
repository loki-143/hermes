import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from src.db import init_db
from src.ingestion import NormalizedMessage, ReconstructedInteraction
from src.interaction_rag import InteractionRAG
from src.dynamic_rag_engine import DynamicRAGEngine
from src.risk_engine import evaluate_response_risk, RiskDecision
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.learning_pipeline import ContinuousLearningPipeline
from src.person_skill_distiller import PersonSpecificExSkillDistiller

class WhatsAppGatewayHandler:
    """
    Production WhatsApp Gateway Handler for Hermes.
    - Dynamic Routing: Dispatches to person-specific skill (lokesh-{contact_slug}-persona) if available.
    - New Contact Onboarding & Continuous Learning: Ingests new turns into SQLite RAG & auto-distills skills.
    - Risk & Approval Gate: Evaluates candidate risk; routes REVIEW/HUMAN_ONLY to HumanApprovalQueue.
    - Metadata Header: Tags outbound messages with source skill provenance.
    """
    def __init__(self, db_path: str = "live_whatsapp.db", skills_dir: str = "/home/lokesh/.hermes/skills"):
        self.db_path = db_path
        self.skills_dir = Path(skills_dir)
        init_db(db_path)
        self.rag = InteractionRAG(db_path)
        self.dynamic_rag = DynamicRAGEngine(db_path)
        self.approval_queue = HumanApprovalQueue(db_path)
        self.learning_pipeline = ContinuousLearningPipeline(self.rag)

    def _get_contact_slug(self, contact_name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '', contact_name.lower())

    def _get_person_skill_path(self, contact_name: str) -> Optional[Path]:
        slug = self._get_contact_slug(contact_name)
        skill_file = self.skills_dir / f"lokesh-{slug}-persona" / "SKILL.md"
        if skill_file.exists():
            return skill_file
        return None

    def process_incoming_message(
        self,
        contact_name: str,
        incoming_text: str,
        candidate_response: str,
        recent_history: Optional[list] = None
    ) -> Dict[str, Any]:
        contact_slug = self._get_contact_slug(contact_name)
        skill_path = self._get_person_skill_path(contact_name)

        # 1. Evaluate Risk Gate
        risk: RiskDecision = evaluate_response_risk(
            candidate_response=candidate_response,
            incoming_message=incoming_text
        )

        # 2. Check if person-specific skill exists
        if skill_path:
            skill_name = f"lokesh-{contact_slug}-persona"
            metadata_tag = f"[Generated via {skill_name} skill]"
            is_known_contact = True
        else:
            skill_name = "default-communication-agent"
            metadata_tag = "[Generated via learning engine (New Contact)]"
            is_known_contact = False

        # 3. Handle High / Medium Risk Routing
        if risk.decision != "AUTO_SEND":
            queue_item = ApprovalItem(
                queue_id=f"gate_{contact_slug}_{int(os.times().elapsed * 1000)}",
                contact_id=contact_name,
                incoming_message=incoming_text,
                candidate_response=candidate_response,
                risk_level=risk.risk_level,
                reason=risk.reason,
                status="PENDING"
            )
            self.approval_queue.enqueue(queue_item)
            return {
                "status": "APPROVAL_REQUIRED",
                "risk_decision": risk.model_dump(),
                "queue_id": queue_item.queue_id,
                "metadata_tag": metadata_tag,
                "outbound_text": f"⚠️ Message held for approval ({risk.reason}).\n\n{metadata_tag}",
                "is_known_contact": is_known_contact
            }

        # 4. Low Risk -> Prepare Outbound Payload
        final_outbound = f"{candidate_response}\n\n{metadata_tag}"

        # 5. Continuous Learning: Index new turn into RAG
        new_interaction = ReconstructedInteraction(
            interaction_id=f"turn_{contact_slug}_{int(os.times().elapsed * 1000)}",
            contact_id=contact_name,
            incoming_message=incoming_text,
            context_history=recent_history or [],
            user_response=candidate_response,
            relationship_category="active_gateway_turn",
            timestamp=datetime.now()
        )
        self.rag.index_interaction(new_interaction)

        return {
            "status": "AUTO_SENT",
            "risk_decision": risk.model_dump(),
            "outbound_text": final_outbound,
            "raw_response": candidate_response,
            "metadata_tag": metadata_tag,
            "skill_name": skill_name,
            "is_known_contact": is_known_contact
        }

    def distill_new_contact_skill(self, chat_file_path: str, contact_name: str) -> str:
        distiller = PersonSpecificExSkillDistiller(
            raw_chat_path=chat_file_path,
            contact_name=contact_name,
            user_name="Loki"
        )
        skill_name = distiller.generate_person_skill()
        return skill_name
