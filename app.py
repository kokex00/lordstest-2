import os
import threading
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_dev")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///discord_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Import and register blueprints
from routes.dashboard import dashboard_bp
from routes.api import api_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Start Discord bot in a separate thread
def start_bot():
    from bot import run_bot
    run_bot()

if __name__ != "__main__":
    # Start bot when running through gunicorn or similar
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
