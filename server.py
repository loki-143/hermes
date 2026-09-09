import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from src.db import init_db
from src.ingestion import parse_whatsapp_chat, reconstruct_interactions
from src.relationship_engine import analyze_relationship_profile
from src.interaction_rag import InteractionRAG
from src.models import ContactProfile
from src.context_assembler import ContextAssembler
from src.risk_engine import evaluate_response_risk

app = Flask(__name__)
DB_PATH = "live_whatsapp.db"

# HTML & Tailwind CSS single page web UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Personal Communication Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen font-sans">
    <div class="max-w-6xl mx-auto p-6 space-y-6">
        
        <!-- Header -->
        <header class="flex items-center justify-between border-b border-slate-800 pb-4">
            <div class="flex items-center space-x-3">
                <div class="bg-emerald-500 p-2.5 rounded-xl text-slate-950 font-bold text-xl">
                    <i class="fab fa-whatsapp"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold text-white">Personal Communication Agent</h1>
                    <p class="text-xs text-slate-400">TDS Engine & RAG Interaction Simulator</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span class="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400 animate-pulse"></span> RAG Loaded
                </span>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-slate-800/60 border border-slate-700/50 p-4 rounded-xl">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Contact Profile</div>
                <div class="text-lg font-bold text-emerald-400 mt-1" id="contact-name">Abhiii 😊</div>
                <div class="text-xs text-slate-400" id="contact-category">Category: Close Friend</div>
            </div>
            <div class="bg-slate-800/60 border border-slate-700/50 p-4 rounded-xl">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Parsed History</div>
                <div class="text-lg font-bold text-blue-400 mt-1">3,661 Messages</div>
                <div class="text-xs text-slate-400">682 Interaction Tuples</div>
            </div>
            <div class="bg-slate-800/60 border border-slate-700/50 p-4 rounded-xl">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Formality Score</div>
                <div class="text-lg font-bold text-amber-400 mt-1">0.10 / 1.0</div>
                <div class="text-xs text-slate-400">Slang & Telugu Code-Switching</div>
            </div>
            <div class="bg-slate-800/60 border border-slate-700/50 p-4 rounded-xl">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Top Emojis</div>
                <div class="text-lg font-bold text-purple-400 mt-1">🥲 🫠 🙂 😭 😂</div>
                <div class="text-xs text-slate-400">Learned Style Vocabulary</div>
            </div>
        </div>

        <!-- Main Section -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- Left Column: Test Playground -->
            <div class="lg:col-span-7 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-4">
                <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                    <i class="fas fa-[#00ff88] fa-paper-plane text-emerald-400"></i>
                    <span>Simulate Incoming Message</span>
                </h2>

                <form id="sim-form" class="space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Incoming Message from Abhiii:</label>
                        <input type="text" id="incoming_text" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 transition" value="Bro fast gaa rammey center ki">
                    </div>

                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Candidate Response (Agent / User):</label>
                        <input type="text" id="candidate_text" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 transition" value="Ostha ra 5 mins lo 😂">
                    </div>

                    <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold py-3 rounded-xl transition flex items-center justify-center space-x-2 text-sm shadow-lg shadow-emerald-900/30">
                        <i class="fas fa-[#00ff88] fa-bolt"></i>
                        <span>Evaluate & Retrieve RAG Context</span>
                    </button>
                </form>

                <!-- Output Card -->
                <div id="result-container" class="hidden space-y-4 pt-2">
                    <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-700 space-y-3">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Risk Decision</span>
                            <span id="risk-badge" class="px-3 py-1 rounded-full text-xs font-bold"></span>
                        </div>
                        <div class="text-xs text-slate-300">
                            <strong>Reason:</strong> <span id="risk-reason" class="text-slate-400"></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column: RAG Matches & TDS Prompt Inspector -->
            <div class="lg:col-span-5 space-y-6">
                
                <!-- RAG Context -->
                <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
                    <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                        <i class="fas fa-[#00ff88] fa-database text-blue-400"></i>
                        <span>Historical RAG Context Matches</span>
                    </h2>
                    <div id="rag-matches" class="space-y-2 text-xs text-slate-400">
                        <p class="italic text-slate-500">Run a simulation to view historical match pairs from chat logs...</p>
                    </div>
                </div>

                <!-- TDS Prompt Assembly -->
                <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
                    <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                        <i class="fas fa-[#00ff88] fa-layer-group text-purple-400"></i>
                        <span>TDS Assembled System Prompt</span>
                    </h2>
                    <pre id="system-prompt" class="bg-slate-950 p-3 rounded-xl text-[11px] text-slate-300 font-mono overflow-x-auto max-h-64 border border-slate-800">Run a simulation to view assembled TDS context...</pre>
                </div>

            </div>
        </div>
    </div>

    <script>
        document.getElementById('sim-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const incoming = document.getElementById('incoming_text').value;
            const candidate = document.getElementById('candidate_text').value;

            const res = await fetch('/api/simulate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({incoming, candidate})
            });

            const data = await res.json();
            
            // Risk Badge
            const badge = document.getElementById('risk-badge');
            badge.innerText = data.risk.decision + " (" + data.risk.risk_level.toUpperCase() + ")";
            if (data.risk.decision === 'AUTO_SEND') {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            } else if (data.risk.decision === 'REVIEW') {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            } else {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30";
            }

            document.getElementById('risk-reason').innerText = data.risk.reason;
            document.getElementById('result-container').classList.remove('hidden');

            // RAG Matches
            const ragDiv = document.getElementById('rag-matches');
            if (data.rag_matches.length > 0) {
                ragDiv.innerHTML = data.rag_matches.map(m => `
                    <div class="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1">
                        <div class="text-blue-400 font-semibold">Incoming: "${m.incoming_message}"</div>
                        <div class="text-emerald-400 font-semibold">Loki (User): "${m.user_response}"</div>
                    </div>
                `).join('');
            } else {
                ragDiv.innerHTML = '<p class="text-slate-500">No close historical matches found.</p>';
            }

            // Assembled System Prompt
            document.getElementById('system-prompt').innerText = data.system_prompt;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/simulate', methods=['POST'])
def simulate():
    payload = request.json or {}
    incoming = payload.get('incoming', '')
    candidate = payload.get('candidate', '')

    rag = InteractionRAG(DB_PATH)
    matches = rag.search_similar_interactions(incoming, contact_id='Abhiii', limit=3)

    risk = evaluate_response_risk(candidate_response=candidate, incoming_message=incoming)

    assembler = ContextAssembler()
    prompt = assembler.build_system_prompt(
        global_style={"avg_sentence_len": 2.94, "code_switch_ratio": 0.0178, "slang_words": {"em": 40, "ledhu": 18, "sare": 9, "ra": 37}},
        contact_profile=ContactProfile(
            contact_id="Abhiii",
            display_name="Abhiii (Abhinaya)",
            relationship_category="close_friend",
            formality_score=0.1,
            preferred_greetings=['sare', 'ledhu', 'ra'],
            top_emojis=['🥲', '🫠', '🙂', '😭', '😂']
        )
    )

    return jsonify({
        "risk": risk.model_dump(),
        "rag_matches": [m.model_dump() for m in matches],
        "system_prompt": prompt
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)
