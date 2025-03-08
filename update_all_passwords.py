
from app import db, create_app
from models import User
from werkzeug.security import generate_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def update_user_password(user):
    """Update a user's password to use proper hashing"""
    # Check for users with plain-text passwords in password_hash field
    if user.password_hash and not user.password_hash.startswith('pbkdf2:sha256:'):
        plain_password = user.password_hash
        user.password_hash = generate_password_hash(plain_password)
        logger.info(f"Updated plain-text password for user {user.id} ({user.email})")
        return True
    elif hasattr(user, 'password') and user.password and not user.password_hash:
        # Legacy 'password' attribute
        plain_password = user.password
        user.password_hash = generate_password_hash(plain_password)
        logger.info(f"Migrated legacy password for user {user.id} ({user.email})")
        return True
    
    return False

def update_all_passwords():
    """Update all users to ensure passwords are properly hashed"""
    with app.app_context():
        users = User.query.all()
        updated_count = 0
        
        for user in users:
            if update_user_password(user):
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            logger.info(f"Successfully updated {updated_count} user passwords")
        else:
            logger.info("No passwords needed updating")

if __name__ == "__main__":
    update_all_passwords()
