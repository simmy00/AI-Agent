#!/usr/bin/env python3
"""
OpenClaw WhatsApp & Chat Channel Server
========================================
Flask server that connects OpenClaw AI to WhatsApp via Twilio Sandbox,
provides a real-time monitoring dashboard, and a simulated WhatsApp UI.

Usage:
    python whatsapp_server.py          # Start server (auto-opens ngrok tunnel)
    python whatsapp_server.py --no-ngrok  # Start without ngrok (if you have your own tunnel)

Routes:
    /webhook       - Twilio WhatsApp webhook (POST)
    /dashboard     - Monitoring dashboard (GET)
    /simulate      - Simulated WhatsApp chat UI (GET)
    /api/messages  - Conversation history API (GET)
    /api/stats     - Statistics API (GET)
    /api/send-simulated - Send simulated message (POST)
    /health        - Health check (GET)
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
#  Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)

# ---------------------------------------------------------------------------
#  Globals (initialized in start_server)
# ---------------------------------------------------------------------------
agent = None
chatbot = None
conversation_log = []
LOG_FILE = Path("data/conversation_log.json")


def _save_log():
    """Persist conversation log to disk"""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(conversation_log, f, indent=2, default=str)
    except Exception as e:
        print(f"[WARN] Could not save log: {e}")


def _load_log():
    """Load conversation log from disk"""
    global conversation_log
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                conversation_log = json.load(f)
    except Exception:
        conversation_log = []


def _log_message(direction, channel, phone, message, response=None,
                 inquiry_type=None, action=None, response_time_ms=None):
    """Log a message to the conversation history"""
    entry = {
        "id": len(conversation_log) + 1,
        "timestamp": datetime.now().isoformat(),
        "direction": direction,  # "inbound" or "outbound"
        "channel": channel,      # "whatsapp" or "web_simulate"
        "phone": phone,
        "message": message,
        "response": response,
        "inquiry_type": inquiry_type,
        "action": action,
        "response_time_ms": response_time_ms,
    }
    conversation_log.append(entry)
    _save_log()
    return entry


# ---------------------------------------------------------------------------
#  Twilio WhatsApp Webhook
# ---------------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """
    Receive incoming WhatsApp messages from Twilio.
    Process through OpenClaw AI and return TwiML response.
    """
    from twilio.twiml.messaging_response import MessagingResponse

    # Extract message data from Twilio
    incoming_msg = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "unknown")
    to_number = request.form.get("To", "unknown")

    print(f"\n[WA] WhatsApp from {from_number}: {incoming_msg}")

    # Process through OpenClaw AI
    start_time = time.time()
    try:
        result = chatbot.handle_message(incoming_msg, channel="whatsapp", user_id=from_number)
        response_text = result.get("response", "Sorry, I could not process your message.")
        inquiry_type = result.get("inquiry_type", "unknown")
        action = result.get("action", "unknown")
    except Exception as e:
        print(f"[ERROR] Processing message: {e}")
        response_text = (
            "I'm sorry, I'm experiencing a temporary issue. "
            "Please try again in a moment, or contact our support team directly."
        )
        inquiry_type = "error"
        action = "error"

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Log the conversation
    _log_message(
        direction="inbound",
        channel="whatsapp",
        phone=from_number,
        message=incoming_msg,
        response=response_text,
        inquiry_type=inquiry_type,
        action=action,
        response_time_ms=elapsed_ms,
    )

    print(f"[BOT] Reply ({elapsed_ms}ms) [{inquiry_type}]: {response_text[:100]}...")

    # Build Twilio TwiML response
    twiml = MessagingResponse()
    twiml.message(response_text)
    return str(twiml), 200, {"Content-Type": "application/xml"}


# ---------------------------------------------------------------------------
#  Dashboard & Simulate Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Redirect to dashboard"""
    return render_template("dashboard.html")


@app.route("/dashboard")
def dashboard():
    """Real-time monitoring dashboard"""
    return render_template("dashboard.html")


@app.route("/simulate")
def simulate():
    """Simulated WhatsApp chat UI for demos"""
    return render_template("simulate.html")


# ---------------------------------------------------------------------------
#  API Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/messages", methods=["GET"])
def api_messages():
    """Return conversation history as JSON"""
    limit = request.args.get("limit", 100, type=int)
    channel = request.args.get("channel", None)

    messages = conversation_log.copy()
    if channel:
        messages = [m for m in messages if m.get("channel") == channel]

    # Return most recent first
    messages = sorted(messages, key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify({"messages": messages[:limit], "total": len(conversation_log)})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Return conversation statistics"""
    total = len(conversation_log)
    if total == 0:
        return jsonify({
            "total_messages": 0,
            "avg_response_time_ms": 0,
            "inquiry_breakdown": {},
            "escalation_count": 0,
            "channels": {},
        })

    # Calculate stats
    response_times = [m.get("response_time_ms", 0) for m in conversation_log if m.get("response_time_ms")]
    avg_rt = int(sum(response_times) / len(response_times)) if response_times else 0

    inquiry_counts = {}
    channel_counts = {}
    escalation_count = 0

    for msg in conversation_log:
        itype = msg.get("inquiry_type", "unknown")
        inquiry_counts[itype] = inquiry_counts.get(itype, 0) + 1

        ch = msg.get("channel", "unknown")
        channel_counts[ch] = channel_counts.get(ch, 0) + 1

        if msg.get("action") == "route_to_human":
            escalation_count += 1

    return jsonify({
        "total_messages": total,
        "avg_response_time_ms": avg_rt,
        "inquiry_breakdown": inquiry_counts,
        "escalation_count": escalation_count,
        "channels": channel_counts,
    })


@app.route("/api/send-simulated", methods=["POST"])
def api_send_simulated():
    """Send a simulated message through the AI (no Twilio needed)"""
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    start_time = time.time()
    try:
        result = chatbot.handle_message(message, channel="web_simulate", user_id="simulator")
        response_text = result.get("response", "Sorry, could not process.")
        inquiry_type = result.get("inquiry_type", "unknown")
        action = result.get("action", "unknown")
    except Exception as e:
        response_text = f"Error: {str(e)}"
        inquiry_type = "error"
        action = "error"

    elapsed_ms = int((time.time() - start_time) * 1000)

    entry = _log_message(
        direction="inbound",
        channel="web_simulate",
        phone="simulator",
        message=message,
        response=response_text,
        inquiry_type=inquiry_type,
        action=action,
        response_time_ms=elapsed_ms,
    )

    return jsonify({
        "response": response_text,
        "inquiry_type": inquiry_type,
        "action": action,
        "response_time_ms": elapsed_ms,
        "id": entry["id"],
    })


@app.route("/api/clear-log", methods=["POST"])
def api_clear_log():
    """Clear conversation log"""
    global conversation_log
    conversation_log = []
    _save_log()
    return jsonify({"status": "cleared"})


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "agent_loaded": agent is not None,
        "total_messages": len(conversation_log),
        "timestamp": datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
#  Server Startup
# ---------------------------------------------------------------------------
def start_server(host="0.0.0.0", port=5000, use_ngrok=True):
    """Initialize the AI agent and start the Flask server"""
    global agent, chatbot

    from agent import RetailAgent, OpenClawChatbot
    from tools import RetailTools

    # Load API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    api_key = openrouter_api_key if openrouter_api_key and openrouter_api_key != "your_openrouter_api_key_here" else groq_api_key
    use_openrouter = bool(openrouter_api_key and openrouter_api_key != "your_openrouter_api_key_here")

    if not api_key or api_key in ("your_groq_api_key_here", "your_openrouter_api_key_here"):
        print("\n[ERROR] No API key configured!")
        print("Add GROQ_API_KEY or OPENROUTER_API_KEY to your .env file")
        sys.exit(1)

    # Initialize tools and agent
    print("\n[SETUP] Loading OpenClaw AI tools...")
    tools = RetailTools("data/products.csv", "data/orders.csv", "data/policy.txt")
    agent = RetailAgent(api_key=api_key, tools=tools, use_openrouter=use_openrouter)
    chatbot = OpenClawChatbot(agent)

    # Load existing conversation log
    _load_log()

    print(f"\n[OK] OpenClaw AI Agent loaded")
    print(f"[LOG] Loaded {len(conversation_log)} previous messages from log")

    # Start ngrok tunnel
    public_url = None
    if use_ngrok:
        try:
            from pyngrok import ngrok as pyngrok_module

            # Check for ngrok auth token
            ngrok_token = os.getenv("NGROK_AUTH_TOKEN")
            if ngrok_token:
                pyngrok_module.set_auth_token(ngrok_token)

            public_url = pyngrok_module.connect(port, "http").public_url
            webhook_url = f"{public_url}/webhook"

            print(f"\n[NGROK] Tunnel active!")
            print(f"   Public URL:  {public_url}")
            print(f"   Webhook URL: {webhook_url}")
            print(f"\n[SETUP] INSTRUCTIONS:")
            print(f"   1. Go to https://console.twilio.com")
            print(f"   2. Navigate to: Messaging > Try it Out > Send a WhatsApp message")
            print(f"   3. Join the sandbox from your phone (send the join code)")
            print(f"   4. Go to Sandbox Settings")
            print(f"   5. Set 'When a message comes in' to:")
            print(f"      {webhook_url}")
            print(f"   6. Set method to HTTP POST")
            print(f"   7. Save and start chatting from your phone!")
        except ImportError:
            print("\n[WARN] pyngrok not installed. Run: pip install pyngrok")
            print("   Starting without ngrok tunnel...")
        except Exception as e:
            print(f"\n[WARN] Could not start ngrok: {e}")
            print("   You can manually run: ngrok http 5000")
            print("   Then set the forwarding URL in Twilio Console")

    print(f"\n{'='*60}")
    print(f"  OpenClaw WhatsApp Server Running")
    print(f"{'='*60}")
    print(f"  Dashboard:    http://localhost:{port}/dashboard")
    print(f"  Simulate:     http://localhost:{port}/simulate")
    print(f"  Health:       http://localhost:{port}/health")
    if public_url:
        print(f"  Webhook:      {public_url}/webhook")
    print(f"{'='*60}\n")

    # Run Flask
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    use_ngrok = "--no-ngrok" not in sys.argv
    port = int(os.getenv("PORT", 5000))
    start_server(port=port, use_ngrok=use_ngrok)
