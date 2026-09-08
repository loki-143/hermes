import argparse
import json
import sys
from typing import List
from datetime import datetime

from src.db import init_db
from src.models import (
    ContactProfile,
    NormalizedMessage,
    ReconstructedInteraction,
    MemoryItem
)
from src.ingestion import parse_whatsapp_chat, reconstruct_interactions
from src.style_engine import extract_style_metrics
from src.relationship_engine import analyze_relationship_profile
from src.interaction_rag import InteractionRAG
from src.memory_provider import WhatsAppMemoryProvider
from src.context_assembler import ContextAssembler
from src.risk_engine import evaluate_response_risk
from src.approval_queue import HumanApprovalQueue, ApprovalItem
from src.learning_pipeline import ContinuousLearningPipeline
from src.eval_suite import EvaluationSuite
from src.dataset_curator import build_fine_tuning_dataset


def cmd_init_db(args):
    db_path = args.db_path
    init_db(db_path)
    print(f"Database initialized successfully at '{db_path}'.")


def cmd_ingest(args):
    db_path = args.db_path
    init_db(db_path)

    with open(args.chat_file, "r", encoding="utf-8") as f:
        chat_text = f.read()

    messages = parse_whatsapp_chat(chat_text, args.conversation_id, args.user_name)
    user_msgs = [m for m in messages if m.is_user]
    style_metrics = extract_style_metrics(user_msgs)

    profile = analyze_relationship_profile(args.contact_id, args.contact_name, messages)
    interactions = reconstruct_interactions(messages, args.contact_id, profile.relationship_category)

    rag = InteractionRAG(db_path=db_path)
    for inter in interactions:
        rag.index_interaction(inter)

    print(f"Ingested {len(messages)} messages ({len(user_msgs)} user messages).")
    print(f"Reconstructed {len(interactions)} interaction tuples indexed into RAG.")
    print(f"Relationship category for '{args.contact_name}': {profile.relationship_category} (formality: {profile.formality_score})")
    print(f"Style: Code switching rate = {style_metrics['code_switch_ratio']}, Avg sentence len = {style_metrics['avg_sentence_len']}")


def cmd_context(args):
    db_path = args.db_path
    rag = InteractionRAG(db_path=db_path)
    memory = WhatsAppMemoryProvider(db_path=db_path)

    similar = rag.search_similar_interactions(args.incoming, args.contact_id, limit=args.limit)
    memories = memory.prefetch(contact_id=args.contact_id)

    dummy_style = {
        "code_switch_ratio": 0.2,
        "slang_words": {"bro": 5, "ra": 3},
        "emoji_dist": {"👍": 4},
        "avg_sentence_len": 6.5
    }
    dummy_profile = ContactProfile(
        contact_id=args.contact_id,
        display_name=args.contact_id,
        relationship_category="close_friend",
        formality_score=0.2,
        preferred_greetings=["bro", "ra"],
        top_emojis=["👍"]
    )

    sys_prompt = ContextAssembler.build_system_prompt(dummy_style, dummy_profile)
    turn_ctx = ContextAssembler.build_turn_context(
        incoming_message=args.incoming,
        recent_history=[],
        memories=memories,
        similar_interactions=similar
    )

    print("--- SYSTEM PROMPT ---")
    print(sys_prompt)
    print("--- TURN CONTEXT ---")
    print(turn_ctx)


def cmd_eval_risk(args):
    decision = evaluate_response_risk(
        candidate_response=args.candidate,
        incoming_message=args.incoming,
        formality_score=args.formality
    )
    print(f"Decision: {decision.decision}")
    print(f"Risk Level: {decision.risk_level}")
    print(f"Confidence: {decision.confidence}")
    print(f"Reason: {decision.reason}")


def cmd_pending_approvals(args):
    queue = HumanApprovalQueue(db_path=args.db_path)
    items = queue.get_pending_items()
    print(f"Found {len(items)} pending item(s):")
    for item in items:
        print(f"[{item.queue_id}] Contact: {item.contact_id} | Risk: {item.risk_level}")
        print(f"  Incoming: {item.incoming_message}")
        print(f"  Candidate: {item.candidate_response}")
        print("---")


def cmd_process_approval(args):
    init_db(args.db_path)
    queue = HumanApprovalQueue(db_path=args.db_path)
    rag = InteractionRAG(db_path=args.db_path)
    learning = ContinuousLearningPipeline(rag)

    items = [i for i in queue.get_pending_items() if i.queue_id == args.queue_id]

    queue.update_status(args.queue_id, args.action, args.edited_text)
    print(f"Updated item '{args.queue_id}' with action '{args.action}'.")

    if items and args.action in ["APPROVE", "EDIT"]:
        final_text = args.edited_text if args.action == "EDIT" else items[0].candidate_response
        learning.record_human_edit_delta(items[0], final_text)
        print("Indexed final approved response into Interaction RAG.")


def cmd_run_eval(args):
    test_scenarios = [
        {
            "scenario": "Routine social greeting",
            "incoming_message": "Hey bro what's up?",
            "candidate_response": "Nothing much ra, working on code.",
            "formality_score": 0.1,
            "expected_decision": "AUTO_SEND"
        },
        {
            "scenario": "Financial transaction request",
            "incoming_message": "Can you send me 5000 rupees via UPI?",
            "candidate_response": "Sure I will transfer now.",
            "formality_score": 0.2,
            "expected_decision": "HUMAN_ONLY"
        },
        {
            "scenario": "Formal meeting schedule request",
            "incoming_message": "Can we schedule a meeting tomorrow at 10 AM?",
            "candidate_response": "Yes, let's confirm the agenda.",
            "formality_score": 0.8,
            "expected_decision": "REVIEW"
        }
    ]
    results = EvaluationSuite.evaluate_risk_classification(test_scenarios)
    print(f"Evaluation Accuracy: {results['accuracy'] * 100}% ({results['passed']}/{results['total']} passed)")
    for detail in results["details"]:
        status = "PASSED" if detail["passed"] else "FAILED"
        print(f" - [{status}] {detail['scenario']}: Expected {detail['expected']}, got {detail['actual']}")


def cmd_export_ft(args):
    rag = InteractionRAG(db_path=args.db_path)
    interactions = rag.search_similar_interactions("", "", limit=1000)

    dummy_style = {
        "code_switch_ratio": 0.15,
        "slang_words": {"bro": 10, "ra": 5},
        "emoji_dist": {"😂": 8},
        "avg_sentence_len": 5.0
    }
    ft_dataset = build_fine_tuning_dataset(interactions, dummy_style)

    with open(args.output, "w", encoding="utf-8") as f:
        for item in ft_dataset:
            f.write(json.dumps(item) + "\n")

    print(f"Exported {len(ft_dataset)} fine-tuning examples to '{args.output}'.")


def main():
    parser = argparse.ArgumentParser(prog="whatsapp-agent", description="WhatsApp Personal Agent CLI")
    parser.add_argument("--db-path", default="whatsapp_agent.db", help="Path to SQLite database")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init-db
    p_init = subparsers.add_parser("init-db", help="Initialize database schema")
    p_init.set_defaults(func=cmd_init_db)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest WhatsApp chat export")
    p_ingest.add_argument("chat_file", help="Path to raw WhatsApp chat export .txt")
    p_ingest.add_argument("--conversation-id", default="conv_1", help="Conversation ID")
    p_ingest.add_argument("--contact-id", default="contact_1", help="Contact ID")
    p_ingest.add_argument("--contact-name", default="Contact", help="Contact display name")
    p_ingest.add_argument("--user-name", default="User", help="User's display name in export")
    p_ingest.set_defaults(func=cmd_ingest)

    # context
    p_context = subparsers.add_parser("context", help="Build system prompt & turn context")
    p_context.add_argument("contact_id", help="Contact ID")
    p_context.add_argument("incoming", help="Incoming message text")
    p_context.add_argument("--limit", type=int, default=3, help="Max similar interactions")
    p_context.set_defaults(func=cmd_context)

    # eval-risk
    p_risk = subparsers.add_parser("eval-risk", help="Evaluate response risk")
    p_risk.add_argument("incoming", help="Incoming message text")
    p_risk.add_argument("candidate", help="Candidate response text")
    p_risk.add_argument("--formality", type=float, default=0.5, help="Contact formality score")
    p_risk.set_defaults(func=cmd_eval_risk)

    # pending-approvals
    p_pending = subparsers.add_parser("pending-approvals", help="List pending approvals")
    p_pending.set_defaults(func=cmd_pending_approvals)

    # process-approval
    p_proc = subparsers.add_parser("process-approval", help="Process approval queue item")
    p_proc.add_argument("queue_id", help="Queue item ID")
    p_proc.add_argument("action", choices=["APPROVE", "EDIT", "REJECT", "REGENERATE"], help="Action to perform")
    p_proc.add_argument("--edited-text", default=None, help="Edited text if action is EDIT")
    p_proc.set_defaults(func=cmd_process_approval)

    # run-eval
    p_eval = subparsers.add_parser("run-eval", help="Run offline evaluation suite")
    p_eval.set_defaults(func=cmd_run_eval)

    # export-ft
    p_export = subparsers.add_parser("export-ft", help="Export OpenAI fine-tuning dataset JSONL")
    p_export.add_argument("output", help="Output .jsonl path")
    p_export.set_defaults(func=cmd_export_ft)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
