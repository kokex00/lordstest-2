"""
Keep Alive utility for maintaining bot uptime
This creates a simple web server that responds to pings
"""

import threading
import time
from flask import Flask
import logging

# Create a simple Flask app for keep alive
keepalive_app = Flask(__name__)

@keepalive_app.route('/')
def home():
    return "Bot is alive! ✅"

@keepalive_app.route('/health')
def health():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "message": "Discord bot is running"
    }

@keepalive_app.route('/ping')
def ping():
    return "pong"

def run_keep_alive():
    """Run the keep alive server"""
    try:
        keepalive_app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        logging.error(f"Keep alive server error: {e}")

def start_keep_alive():
    """Start the keep alive server in a separate thread"""
    t = threading.Thread(target=run_keep_alive)
    t.daemon = True
    t.start()
    logging.info("Keep alive server started on port 8080")