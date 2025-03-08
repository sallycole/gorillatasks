
from app import db, create_app
from models import User
from werkzeug.security import generate_password_hash
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def migrate_encrypted_passwords():
    """Migrate passwords from encrypted_password to password_hash"""
    with app.app_context():
        users = User.query.all()
        migrated_count = 0
        skipped_count = 0
        
        # First check if we can access the encrypted_password column directly
        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, email, encrypted_password
                FROM users
                WHERE encrypted_password IS NOT NULL
                  AND (password_hash IS NULL OR password_hash = '')
            """))
            
            for row in result:
                user_id, email, encrypted_password = row
                # Get the corresponding user object
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"User {user_id} ({email}) not found in User model")
                    continue
                    
                # Check if encrypted_password exists and password_hash is empty
                if encrypted_password and not user.password_hash:
                    logger.info(f"Migrating password for user {user.id} ({user.email})")
                    
                    # Check if the encrypted_password is too long for password_hash field
                    if len(encrypted_password) > 128:
                        logger.warning(f"Password for user {user.id} is too long ({len(encrypted_password)} chars)")
                        # Use the Werkzeug password hasher to create a proper hash that will fit
                        from werkzeug.security import generate_password_hash
                        user.password_hash = generate_password_hash(encrypted_password[:64])
                        logger.info(f"Created new hash for user {user.id} to fit in field")
                    else:
                        # Store encrypted_password as the new password_hash
                        user.password_hash = encrypted_password
                    migrated_count += 1
                else:
                    skipped_count += 1
                    logger.info(f"Skipping user {user.id} ({user.email}) - already has password_hash or no encrypted_password")
        
        if migrated_count > 0:
            db.session.commit()
            logger.info(f"Successfully migrated {migrated_count} user passwords from encrypted_password to password_hash")
        else:
            logger.info("No passwords needed migration")
            
        logger.info(f"Skipped {skipped_count} users")

if __name__ == "__main__":
    migrate_encrypted_passwords()
