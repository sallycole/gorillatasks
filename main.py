import logging
from app import app, socketio

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Flask-SocketIO application on port 5000")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise