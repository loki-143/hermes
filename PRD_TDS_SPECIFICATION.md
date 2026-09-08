# Master Architectural Specification & Product Requirements Document (PRD/TDS)
**Project Name:** WhatsApp Personal Communication Agent (`ex-skill` + Hermes Integration)  
**Repository:** `/home/lokesh/projects/whatsapp-agent`  
**Architectural Baseline:** Hermes Agent v0.21.0 + `ex-skill` Core Subsystem  

---

## 1. Executive Summary & Core Philosophy
The objective is an autonomous, context-aware, style-matched personal WhatsApp communication agent built on top of Hermes Agent. 
It enables the assistant to converse in the user's authentic personal tone, varying by contact relationship, historical conversation patterns, and remembered facts/episodes.

### Key Invariants
1. **RAG & Memory First, Fine-Tuning Later:** Fine-tuning is forbidden until RAG, memory, relationship profiles, and human approval queues are fully verified.
2. **Two-Sided Learning:** The system MUST ingest and index $(Contact\_Message, Context, User\_Response)$ tuples. Outgoing user messages alone are insufficient.
3. **Hermes Core Invariants:**
   - Prompt caching is sacred (system prompt is byte-stable; dynamic context is injected via user/tool messages or prefetch).
   - Strict role alternation (never two assistant or two user messages in a row).
   - Absolute data privacy (zero committing of raw WhatsApp exports, real credentials, or PII).
4. **Autonomous Single-Agent Execution:** Development proceeds via an autonomous wake-up loop executing task-by-task.

---

## 2. Subsystem & Component Architecture

```
                               ┌──────────────────────────────────────────┐
                               │           WHATSAPP PLATFORM              │
                               └────────────────────┬─────────────────────┘
                                                    │
                                                    ▼
                               ┌──────────────────────────────────────────┐
                               │   HERMES GATEWAY (plugins/platforms/wa)  │
                               └────────────────────┬─────────────────────┘
                                                    │
                                                    ▼
                               ┌──────────────────────────────────────────┐
                               │     HERMES CORE AGENT (run_agent.py)     │
                               └──────────┬────────────────────┬──────────┘
                                          │                    │
                                          ▼                    ▼
                        ┌───────────────────┐        ┌───────────────────┐
                        │ EX-SKILL ENGINE   │        │ MEMORY PROVIDER   │
                        │ (Style & RAG)     │        │ (Facts/Episodes)  │
                        └─────────┬─────────┘        └─────────┬─────────┘
                                  │                            │
                                  └──────────────┬─────────────┘
                                                 │
                                                 ▼
                               ┌──────────────────────────────────────────┐
                               │      CONTEXT ENGINE / LLM ASSEMBLY       │
                               └────────────────────┬─────────────────────┘
                                                    │
                                                    ▼
                               ┌──────────────────────────────────────────┐
                               │      RISK EVALUATOR & POLICY GATE        │
                               └──────────┬────────────────────┬──────────┘
                                          │                    │
                                     (Low Risk)           (High Risk)
                                          │                    │
                                          ▼                    ▼
                                  ┌───────────────┐   ┌──────────────────┐
                                  │   AUTO-SEND   │   │  HUMAN APPROVAL  │
                                  │   DELIVERY    │   │  QUEUE (Telegram/│
                                  └───────────────┘   │  Discord/Web)    │
                                                      └──────────────────┘
```

### Component Roles
1. **`ex-skill` Engine (`plugins/ex_skill/` & `ex_skill/`)**:
   - Parses raw WhatsApp chat exports (`.txt`/zip).
   - Normalizes messages into structured interactions.
   - Computes global user style metrics (vocabulary, slang, Telugu/English code-switching, emoji distributions, sentence length).
   - Generates person-specific relationship profiles (formality, addressing terms, shared topics).
   - Maintains an interaction RAG vector/FTS index for similar response retrieval.
2. **Hermes Memory Provider (`plugins/memory/whatsapp_memory/`)**:
   - Implements `MemoryProvider` ABC (`agent/memory_provider.py`).
   - Extracts semantic, episodic, relationship, temporal, and preference facts.
   - Injects pre-fetched facts into turns via `prefetch()` / `sync_turn()`.
3. **Gateway & WhatsApp Adapter (`plugins/platforms/whatsapp/`)**:
   - Built-in Baileys bridge / WhatsApp Cloud API adapter.
   - Receives inbound messages, maps sender IDs to contact profiles, and routes turns.
4. **Risk Evaluator & Approval Queue (`ex_skill/safety/`)**:
   - Evaluates risk score (financial, legal, commitments, account security, sensitive topics).
   - Routes low-risk messages to auto-send; high-risk messages land in approval queue (Telegram/CLI/Web).

---

## 3. Storage & Schema Specifications

### Storage Engines
- **Metadata & Profiles:** SQLite (`~/.hermes/whatsapp_agent.db`).
- **RAG Vector Search:** SQLite-VSS / LanceDB / FTS5 hybrid index.

### Core Schemas

#### 3.1 Normalized Message
```json
{
  "id": "wa_msg_12345",
  "conversation_id": "contact_919876543210",
  "timestamp": "2026-09-09T14:30:00Z",
  "sender_id": "919876543210",
  "sender_name": "Rahul",
  "message_text": "Bro when are you starting?",
  "is_user": false,
  "reply_to_id": null,
  "metadata": {}
}
```

#### 3.2 Reconstructed Interaction Tuple (Two-Sided Learning)
```json
{
  "interaction_id": "inter_9876",
  "contact_id": "contact_919876543210",
  "incoming_message": "Bro when are you starting?",
  "context_history": ["Rahul: I am ready at home."],
  "user_response": "Starting now ra 🚗",
  "relationship_category": "close_friend",
  "timestamp": "2026-09-09T14:31:00Z"
}
```

#### 3.3 Contact Relationship Profile
```json
{
  "contact_id": "contact_919876543210",
  "display_name": "Rahul",
  "category": "close_friend",
  "formality_score": 0.15,
  "preferred_greetings": ["rey", "bro"],
  "code_switching_rate": 0.65,
  "emoji_frequency": 0.8,
  "top_emojis": ["😂", "🚗", "👍"],
  "avg_response_length": 4.5,
  "known_facts": ["Works at TechCorp", "Enjoys badminton"],
  "updated_at": "2026-09-09T15:00:00Z"
}
```

---

## 4. Implementation Phasing Roadmap

| Phase | Description | Deliverables / Output | Status |
| :--- | :--- | :--- | :--- |
| **P0** | **Reconnaissance & Architecture** | Complete environment scan, TDS/PRD creation, state tracking initialization | **IN_PROGRESS** |
| **P1** | **Foundation & Environment** | Scaffold `/home/lokesh/projects/whatsapp-agent`, SQLite schema, core tests | READY |
| **P2** | **WhatsApp Data Ingestion** | Parser for export formats, normalization, interaction tuple builder | READY |
| **P3** | **Communication Style Subsystem** | Global style metric extractor, vocabulary/code-switching analysis | READY |
| **P4** | **Relationship Profile Engine** | Contact-specific relationship classifier and profile manager | READY |
| **P5** | **Hermes Memory Provider Integration** | `MemoryProvider` implementation for semantic/episodic facts | READY |
| **P6** | **Historical Interaction RAG** | Vector/FTS search for similar past incoming-response pairs | READY |
| **P7** | **Hermes Gateway & Orchestration** | Gateway hook integration, prompt assembler, turn execution | READY |
| **P8** | **Risk Engine & Policy Gate** | Intent classifier, risk matrix, decision engine (`AUTO_SEND` vs `APPROVAL`) | READY |
| **P9** | **Human Approval Queue** | Telegram/CLI approval interface (Approve / Edit / Reject / Regenerate) | READY |
| **P10**| **Continuous Learning Loop** | Human edit delta logger, periodic profile & memory reinforcement | READY |
| **P11**| **Evaluation & Safety Benchmark** | Offline eval suite (Style match, Memory recall, Safety boundaries) | READY |
| **P12**| **Fine-Tuning Dataset Builder** | Dataset curation pipeline (conditional, post-verification) | READY |

---

## 5. Definition of Done & Verification Criteria
1. Full End-to-End Pipeline Operational:
   WhatsApp Inbound $\rightarrow$ Gateway $\rightarrow$ Hermes $\rightarrow$ Contact Identification $\rightarrow$ Relationship Retrieval $\rightarrow$ Fact Memory Retrieval $\rightarrow$ Historical RAG Retrieval $\rightarrow$ Style Prompt Assembly $\rightarrow$ Response Generation $\rightarrow$ Risk Evaluation $\rightarrow$ Auto-Send / Approval $\rightarrow$ Delivery.
2. 100% Passing Test Suite: All unit, integration, and contract tests pass cleanly via `pytest` without mocking core invariants.
3. Privacy & Security Invariants Maintained: Zero real credentials, tokens, or PII committed.
