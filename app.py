
import os
import logging
from flask import Flask, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['CORS_HEADERS'] = 'Content-Type'
    
    # Configure app
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_only")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@0.0.0.0:5432/postgres")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize extensions
    csrf.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')
    
    # Import WebSocket events
    import events  # noqa: F401
    
    with app.app_context():
        try:
            # Import models first
            import models  # noqa: F401
            
            # Register blueprints after models are imported
            from routes import auth_bp, curriculum_bp, dashboard_bp, archive_bp
            app.register_blueprint(auth_bp, url_prefix='/auth')
            app.register_blueprint(curriculum_bp, url_prefix='/curriculum')
            app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
            app.register_blueprint(archive_bp, url_prefix='/archive')
            
            # Register root route
            @app.route('/')
            def root():
                return redirect(url_for('dashboard.index'))
            
            logger.info("Registered blueprints: auth, curriculum, dashboard, archive")
            
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Add debug logging for registered routes
            logger.info("Available routes:")
            for rule in app.url_map.iter_rules():
                logger.debug(f"Route: {rule.rule} -> {rule.endpoint} [{','.join(rule.methods)}]")
            logger.info("Blueprints registered successfully")
            
            # Log the complete URL map
            logger.debug("Complete URL map:")
            logger.debug(app.url_map)
            
            @app.errorhandler(404)
            def not_found_error(error):
                logger.error(f"404 Error: {error}")
                return jsonify({"status": "error", "message": "Resource not found"}), 404

            @app.errorhandler(500)
            def internal_error(error):
                logger.error(f"500 Error: {error}")
                db.session.rollback()
                return jsonify({"status": "error", "message": "Internal server error"}), 500
        except Exception as e:
            logger.error(f"Error during application initialization: {str(e)}")
            raise
    
    return app

# Create the application instance
app = create_app()
