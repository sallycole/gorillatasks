
from app import db, create_app
from models import User
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def reset_phoebezcole_password():
    """Reset password for phoebezcole@gmail.com to match original encrypted_password"""
    with app.app_context():
        # Get the user
        user = User.query.filter_by(email='phoebezcole@gmail.com').first()
        
        if not user:
            logger.error("User phoebezcole@gmail.com not found")
            return False
            
        # Get the encrypted_password directly from the database
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT encrypted_password FROM users WHERE email = 'phoebezcole@gmail.com'"))
            row = result.fetchone()
            
            if not row or not row[0]:
                logger.error("No encrypted_password found for phoebezcole@gmail.com")
                return False
                
            encrypted_password = row[0]
            logger.info(f"Found encrypted_password: {encrypted_password}")
            
            # Set the password using the original encrypted_password
            logger.info("Setting password_hash to original encrypted_password")
            
            # Update the user object
            user.password_hash = encrypted_password
            db.session.commit()
            
            logger.info("Password reset successful!")
            return True

if __name__ == "__main__":
    reset_phoebezcole_password()
