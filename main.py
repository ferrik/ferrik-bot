"""
FerrikFoot Bot - Telegram Food Delivery Platform
Deploy на Render через GitHub
"""

import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "bot": "FerrikFoot v3.0"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробка webhook від Telegram"""
    try:
        update = request.json
        logger.info(f"📥 Update: {update.get('update_id')}")
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
