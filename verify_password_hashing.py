
from app import db, create_app
from models import User
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def verify_password_hashing():
    """Check the current state of password hashing in the database"""
    with app.app_context():
        # First, check if 'password' column exists in the users table
        with db.engine.connect() as conn:
            # Get table columns info
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """))
            columns = [row[0] for row in result]
            
            logger.info(f"Columns in users table: {', '.join(columns)}")
            has_password_column = 'password' in columns
            
            if has_password_column:
                # Get password data directly
                result = conn.execute(text("""
                    SELECT id, email, password, password_hash
                    FROM users
                """))
                
                logger.info("\nUser password data:")
                for row in result:
                    user_id, email, password, password_hash = row
                    logger.info(f"User {user_id} ({email}):")
                    logger.info(f"  - password: {'[PRESENT]' if password else '[EMPTY]'}")
                    logger.info(f"  - password_hash: {'[PRESENT]' if password_hash else '[EMPTY]'}")
            else:
                logger.info("No 'password' column exists in the users table")
        
        # Then check User objects as before
        users = User.query.all()
        total_users = len(users)
        hashed_passwords = 0
        plaintext_passwords = 0
        missing_passwords = 0
        legacy_passwords = 0
        
        for user in users:
            if user.password_hash is None:
                missing_passwords += 1
                logger.info(f"User {user.id} ({user.email}): Missing password hash")
                if hasattr(user, 'password') and user.password:
                    legacy_passwords += 1
                    logger.info(f"  - Has legacy 'password' attribute in Python object")
            elif user.password_hash.startswith('pbkdf2:sha256:'):
                hashed_passwords += 1
                logger.info(f"User {user.id} ({user.email}): Password properly hashed")
            else:
                plaintext_passwords += 1
                logger.info(f"User {user.id} ({user.email}): Password in plain text format")
        
        # Print summary
        logger.info(f"\nPassword format summary:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Properly hashed passwords: {hashed_passwords} ({(hashed_passwords/total_users)*100 if total_users > 0 else 0:.1f}%)")
        logger.info(f"  Plain text passwords: {plaintext_passwords} ({(plaintext_passwords/total_users)*100 if total_users > 0 else 0:.1f}%)")
        logger.info(f"  Missing passwords: {missing_passwords} ({(missing_passwords/total_users)*100 if total_users > 0 else 0:.1f}%)")
        logger.info(f"  Users with legacy 'password' attribute: {legacy_passwords}")
        logger.info(f"  Database has 'password' column: {has_password_column}")

if __name__ == "__main__":
    verify_password_hashing()
