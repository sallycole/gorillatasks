import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import pytz

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

app = Flask(__name__)
csrf.init_app(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_only")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

def init_app():
    with app.app_context():
        import models  # noqa: F401
        import routes  # noqa: F401
        
        db.create_all()
        
        # Register blueprints
        from routes import auth_bp, curriculum_bp, dashboard_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(curriculum_bp)
        app.register_blueprint(dashboard_bp)

init_app()
