import os
import json
import sqlite3
import threading
from flask import Flask, render_template_string, request, jsonify
from src.whatsapp_gateway import WhatsAppGatewayHandler
from src.telegram_bridge import TelegramGatewayBridge
from src.telegram_bot_sender import TelegramBotSender
from src.telegram_bot_listener import TelegramBotListener

app = Flask(__name__)
DB_PATH = "live_whatsapp.db"
bot_sender = TelegramBotSender(db_path=DB_PATH)
bridge = TelegramGatewayBridge(db_path=DB_PATH)
listener = TelegramBotListener(db_path=DB_PATH)

# Start background Telegram Poller thread if explicitly enabled (to prevent polling conflict with Hermes Gateway)
if os.getenv("ENABLE_TELEGRAM_POLLER", "0").lower() in ("1", "true", "yes"):
    def run_telegram_poller():
        listener.start_polling_loop()

    poller_thread = threading.Thread(target=run_telegram_poller, daemon=True)
    poller_thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Personal Communication Agent Gateway</title>
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
                    <h1 class="text-xl font-bold text-white">WhatsApp Gateway & Routing Engine</h1>
                    <p class="text-xs text-slate-400">Dynamic Contact Skill Dispatcher & Learning System</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span class="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Dynamic Gateway Active
                </span>
            </div>
        </header>

        <!-- Main Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- Left Column: WhatsApp Message Simulator -->
            <div class="lg:col-span-7 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-4">
                <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                    <i class="fas fa-paper-plane text-emerald-400"></i>
                    <span>Simulate Inbound Gateway Message</span>
                </h2>

                <form id="gw-form" class="space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Select Sender Contact:</label>
                        <select id="contact_name" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 transition">
                            <option value="Frndu" selected>Frndu (40,961 messages - lokesh-frndu-persona skill)</option>
                            <option value="Abhiii">Abhiii (3,661 messages - lokesh-abhiii-persona skill)</option>
                            <option value="Rahul">Rahul (New Contact - Auto Learning Engine)</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Incoming Message Text:</label>
                        <input type="text" id="incoming_text" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 transition" value="Rey cheppu raww... em chesthunnav?">
                    </div>

                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">Candidate Generated Reply:</label>
                        <input type="text" id="candidate_text" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 transition" value="em ledhu ra... work lo unna 🫠">
                    </div>

                    <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold py-3 rounded-xl transition flex items-center justify-center space-x-2 text-sm shadow-lg shadow-emerald-900/30">
                        <i class="fas fa-bolt"></i>
                        <span>Process via Gateway Router</span>
                    </button>
                </form>

                <!-- Output Card -->
                <div id="result-container" class="hidden space-y-4 pt-2">
                    <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-700 space-y-3">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Gateway Processing Result</span>
                            <span id="status-badge" class="px-3 py-1 rounded-full text-xs font-bold"></span>
                        </div>

                        <div>
                            <div class="text-xs font-semibold text-slate-400 mb-1">Outbound Message Payload:</div>
                            <pre id="outbound-text" class="bg-slate-950 p-3 rounded-xl text-xs text-emerald-400 font-mono whitespace-pre-wrap border border-slate-800"></pre>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column: RAG Few-Shot Matches & Prompt Inspector -->
            <div class="lg:col-span-5 space-y-6">
                
                <!-- RAG Context -->
                <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
                    <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                        <i class="fas fa-database text-blue-400"></i>
                        <span>Dynamic RAG Few-Shot Matches</span>
                    </h2>
                    <div id="rag-matches" class="space-y-2 text-xs text-slate-400">
                        <p class="italic text-slate-500">Submit a simulation to view matched turns from chat history...</p>
                    </div>
                </div>

                <!-- Assembled Instruction -->
                <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 space-y-3">
                    <h2 class="text-md font-semibold text-slate-200 flex items-center space-x-2">
                        <i class="fas fa-layer-group text-purple-400"></i>
                        <span>Assembled Dynamic Prompt</span>
                    </h2>
                    <pre id="system-prompt" class="bg-slate-950 p-3 rounded-xl text-[11px] text-slate-300 font-mono overflow-x-auto max-h-64 border border-slate-800">Submit a simulation to view in-context prompt...</pre>
                </div>

            </div>
        </div>
    </div>

    <script>
        document.getElementById('gw-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const contact_name = document.getElementById('contact_name').value;
            const incoming_text = document.getElementById('incoming_text').value;
            const candidate_text = document.getElementById('candidate_text').value;

            const res = await fetch('/api/gateway-process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({contact_name, incoming_text, candidate_text})
            });

            const data = await res.json();
            
            // Status Badge
            const badge = document.getElementById('status-badge');
            badge.innerText = data.gateway_result.status;
            if (data.gateway_result.status === 'AUTO_SENT') {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            } else {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            }

            document.getElementById('outbound-text').innerText = data.gateway_result.outbound_text;
            document.getElementById('result-container').classList.remove('hidden');

            // RAG Matches
            const ragDiv = document.getElementById('rag-matches');
            if (data.rag_matches && data.rag_matches.length > 0) {
                ragDiv.innerHTML = data.rag_matches.map(m => `
                    <div class="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1">
                        <div class="text-blue-400 font-semibold">Incoming: "${m.incoming_message}"</div>
                        <div class="text-emerald-400 font-semibold">Loki: "${m.user_response}"</div>
                    </div>
                `).join('');
            } else {
                ragDiv.innerHTML = '<p class="text-slate-500">No close historical matches found (New contact mode).</p>';
            }

            // System Prompt
            document.getElementById('system-prompt').innerText = data.system_instruction;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/gateway-process', methods=['POST'])
def gateway_process():
    payload = request.json or {}
    contact_name = payload.get('contact_name', 'Frndu')
    incoming_text = payload.get('incoming_text', '')
    candidate_text = payload.get('candidate_text', '')

    bridge_res = bridge.handle_inbound_whatsapp(
        contact_name=contact_name,
        incoming_text=incoming_text,
        candidate_response=candidate_text
    )

    if bridge_res['action'] == 'TELEGRAM_NOTIFY_AND_HOLD':
        bot_sender.send_telegram_card(bridge_res['queue_id'])

    gw = WhatsAppGatewayHandler(db_path=DB_PATH)
    prompt_data = gw.dynamic_rag.assemble_fewshot_prompt(
        incoming_message=incoming_text,
        contact_id=contact_name,
        limit=5
    )

    return jsonify({
        "gateway_result": {
            "status": "APPROVAL_REQUIRED" if bridge_res['action'] == 'TELEGRAM_NOTIFY_AND_HOLD' else "AUTO_SENT",
            "outbound_text": bridge_res['whatsapp_response'] or f"⚠️ Held for approval. Card delivered to Telegram.\n\n{bridge_res['telegram_payload']['text']}",
            "queue_id": bridge_res.get('queue_id')
        },
        "rag_matches": prompt_data['matched_interactions'],
        "system_instruction": prompt_data['system_instruction']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)
