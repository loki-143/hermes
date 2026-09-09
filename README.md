# WhatsApp Personal Communication Agent (`ex-skill` + Hermes Integration)

> **AI-Powered Personal WhatsApp Communication System integrated with NousResearch Hermes Agent.**  
> Learns your authentic texting style from historical WhatsApp chat exports, dispatches person-specific persona skills, enforces dynamic few-shot RAG retrieval, and protects consequential communication via a risk-gated human approval queue.

---

## 🌟 Key Features

1. **Person-Specific `ex-skill` Architecture:**
   - Automatically distills 5-Layer persona skills for individual contacts (e.g., `lokesh-frndu-persona`, `lokesh-abhiii-persona`).
   - Learns your authentic Telugu-English code switching (`ra`, `ledhu`, `sare`, `avuna`, `enti`, `chudu`), response brevity (1–4 words average), punctuation habits (`...`), and emoji distributions (`🥲`, `🫠`, `🙂`, `😭`, `😂`).

2. **Dynamic Few-Shot RAG Engine (`src/dynamic_rag_engine.py`):**
   - Eliminates generic AI persona hallucinations by performing turn-time token-overlap matching over your entire chat history (e.g. 40,961 messages for Frndu).
   - Injects the top 5 exact historical turns directly into the LLM system prompt right before generation.

3. **Time Commitment & Risk Gate (`src/risk_engine.py`):**
   - Automatically intercepts financial, legal, password, or time commitment messages (e.g. *"5:00 ki ready eh na?"*).
   - Classifies messages into `AUTO_SEND`, `REVIEW`, or `HUMAN_ONLY`.
   - Holds `REVIEW` / `HUMAN_ONLY` messages in `HumanApprovalQueue` for your explicit confirmation before sending.

4. **Continuous Learning Pipeline (`src/learning_pipeline.py`):**
   - Ingests new active turns and records your manual edit deltas when approving queued messages, continuously re-indexing learned responses into the RAG store.

5. **Integrated Hermes Gateway & Web Dashboard (`src/whatsapp_gateway.py`, `server.py`):**
   - Outbound messages are tagged with provenance metadata headers (e.g. `[Generated via lokesh-frndu-persona skill]`).
   - Includes a single-page Tailwind CSS web simulator for live testing.

---

## 🏗️ System Architecture

```
                                  WHATSAPP
                                     │
                                     ▼
                          WHATSAPP GATEWAY HANDLER
                       (src/whatsapp_gateway.py)
                                     │
                                     ▼
                        HERMES ROUTER & SKILL MATCH
               ┌─────────────────────┴─────────────────────┐
               ▼                                           ▼
      [ Known Contact Skill ]                     [ New Contact Engine ]
    lokesh-{contact}-persona                    Auto-onboards & distills
               │                                           │
               └─────────────────────┬─────────────────────┘
                                     │
                                     ▼
                          DYNAMIC FEW-SHOT RAG
                      (src/dynamic_rag_engine.py)
              Queries SQLite FTS5 RAG (40k+ chat turns)
                                     │
                                     ▼
                            EXISTING HERMES LLM
                    (Gemini 3.6 Flash / Claude 3.5/3.7)
                                     │
                                     ▼
                          RISK ENGINE EVALUATION
                           (src/risk_engine.py)
                                     │
               ┌─────────────────────┴─────────────────────┐
               ▼                                           ▼
         [ AUTO_SEND ]                           [ REVIEW / HUMAN_ONLY ]
    Low-risk routine message                  Consequential / time commitment
    Sends reply on WhatsApp                  Enqueues in HumanApprovalQueue
```

---

## 🛠️ Installation & Hermes Integration

### 1. Prerequisites
- Python 3.11+
- NousResearch Hermes Agent installed (`~/.hermes/`)
- `uv` package manager (optional, recommended)

### 2. Repository Setup
```bash
git clone https://github.com/loki-143/hermes.git
cd hermes
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Initialize Database & Ingest WhatsApp Chat Export
Export your WhatsApp chat without media (`.txt` file) and place it under `data/raw/`.

```bash
# Initialize SQLite schema
whatsapp-agent init-db --db live_whatsapp.db

# Distill person-specific skill and ingest chat history
python3 src/person_skill_distiller.py
```
This generates the executable skill at `~/.hermes/skills/lokesh-{contact}-persona/SKILL.md` and indexes interaction pairs into SQLite.

---

## 🖥️ How to Use & Integrate with Hermes Agent

### A. Invoke via Hermes CLI
You can invoke the distilled persona skill directly inside Hermes CLI:

```bash
hermes chat -q "Using skill: lokesh-frndu-persona. Respond as Loki to incoming message from Frndu: 'Rey cheppu raww... em chesthunnav?'"
```

### B. Run as a Hermes Autonomous Cron Job
To run an autonomous verification and update loop every 45 minutes:

```bash
hermes cron create \
  --name "whatsapp-agent-autonomous-loop" \
  --schedule "every 45m" \
  --deliver "origin" \
  --workdir "/home/lokesh/projects/whatsapp-agent" \
  --prompt "Autonomous execution wake-up for WhatsApp Agent project. Read IMPLEMENTATION_STATUS.md, verify test suite, and continue autonomous development loop."
```

### C. Launch the Web Gateway Simulator
Start the Flask & Cloudflare live web dashboard:

```bash
python3 server.py
# Web dashboard runs on http://localhost:8090
```

---

## 💻 Unified Command-Line Interface (`whatsapp-agent`)

The system provides a built-in CLI for all operations:

```bash
# 1. Initialize SQLite Database
whatsapp-agent init-db --db demo.db

# 2. Ingest raw WhatsApp chat export
whatsapp-agent ingest data/raw/chat.txt --contact-id "Frndu" --db demo.db

# 3. Assemble TDS System Prompt & Turn Context
whatsapp-agent context "Frndu" "Rey cheppu raww..." --db demo.db

# 4. Evaluate Response Risk
whatsapp-agent eval-risk "ha ready eh 🫠" --incoming "ok aithe 5:00 ki ready eh na?"
# Output: Decision: REVIEW | Risk Level: medium | Reason: Time commitment / specific time pattern (5:00)

# 5. Inspect Pending Human Approvals
whatsapp-agent pending-approvals --db demo.db

# 6. Process Approval (Approve / Edit / Reject)
whatsapp-agent process-approval <QUEUE_ID> --action EDIT --edit-text "ledhu 5:30 ki ostha ra 🫠" --db demo.db

# 7. Run Offline Risk Safety Suite
whatsapp-agent run-eval

# 8. Export Fine-Tuning SFT JSONL Dataset
whatsapp-agent export-ft dataset.jsonl --db demo.db
```

---

## 🧪 Testing & Verification

Run the full automated test suite (33 tests covering DB, ingestion, RAG, risk engine, approval queue, gateway, and distillers):

```bash
cd /home/lokesh/projects/whatsapp-agent
.venv/bin/pytest tests/ -v
```

```
============================== 33 passed in 0.16s ==============================
```

---

## 📂 Project Directory Structure

```
.
├── PRD_TDS_SPECIFICATION.md   # Master Architectural & PRD Document
├── IMPLEMENTATION_STATUS.md    # Master Task & Phase Tracker (P0 to P12)
├── pyproject.toml              # Build & dependency specification
├── server.py                   # Flask + Tailwind Web Gateway Simulator
├── src/
│   ├── db.py                   # SQLite schema initialization
│   ├── models.py               # Pydantic data models
│   ├── ingestion.py            # WhatsApp export parser & pair reconstructor
│   ├── style_engine.py         # Global communication style extractor
│   ├── relationship_engine.py  # Formality & relationship classifier
│   ├── memory_provider.py      # Hermes MemoryProvider integration
│   ├── interaction_rag.py      # Token-overlap & FTS5 similarity search
│   ├── dynamic_rag_engine.py   # Turn-time Few-Shot RAG prompt builder
│   ├── context_assembler.py    # TDS prompt hierarchy builder
│   ├── risk_engine.py          # Risk classification & safety gate
│   ├── approval_queue.py       # Human approval queue manager
│   ├── learning_pipeline.py    # Edit feedback recorder & RAG re-indexer
│   ├── person_skill_distiller.py # Person-specific ex-skill generator
│   ├── whatsapp_gateway.py     # Production WhatsApp gateway handler
│   ├── eval_suite.py           # Offline evaluation suite
│   ├── dataset_curator.py      # SFT JSONL dataset exporter
│   └── cli.py                  # CLI entry point (`whatsapp-agent`)
└── tests/                      # Pytest suite (33 passing unit/integration tests)
```

---

## 📄 License

MIT License © 2026 Lokesh Vasu Dev Chilla. Built for NousResearch Hermes Agent ecosystem.
