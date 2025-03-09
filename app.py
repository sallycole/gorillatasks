
import os
import logging
from flask import Flask, redirect, url_for, flash, request
from flask_login import LoginManager, current_user
from flask_socketio import SocketIO
from flask_talisman import Talisman
from sqlalchemy.exc import OperationalError
from flask_sqlalchemy import SQLAlchemy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

# Initialize extensions
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)

    # Configure Jinja2 to preserve DOCTYPE declarations
    app.jinja_options = dict(app.jinja_options)
    app.jinja_options.setdefault('keep_trailing_newline', True)

    # Database configuration
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # For deployment on platforms like Heroku
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info(f"Database URL configured: {database_url.split('@')[0]}@[REDACTED]")
    else:
        # Default to SQLite for development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///curriculum.db'
        logger.info("Using SQLite database")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)

    # Import models after initializing db to avoid circular imports
    import models

    # Security headers with Talisman (commented out for development)
    # talisman = Talisman(app, content_security_policy=None)

    # Set up login manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    # Register blueprints
    from routes import auth_bp, curriculum_bp, inventory_bp, archive_bp, todo_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(curriculum_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(todo_bp)

    # Register test blueprint if available
    try:
        from routes_test import test_bp
        app.register_blueprint(test_bp)
    except ImportError:
        pass

    logger.info(f"Registered blueprints: auth, curriculum, dashboard, archive, todo")

    @app.route('/')
    def root():
        if current_user.is_authenticated:
            return redirect(url_for('inventory.index'))
        else:
            return redirect(url_for('auth.login'))

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except OperationalError as e:
            logger.error(f"Error creating database tables: {str(e)}")

    # Log available routes
    logger.info("Available routes:")
    for rule in app.url_map.iter_rules():
        logger.debug(f"Route: {rule} -> {rule.endpoint} {rule.methods}")

    logger.info("Blueprints registered successfully")
    logger.debug(f"Complete URL map:\n{app.url_map}")

    return app

# Create the application instance
app = create_app()
