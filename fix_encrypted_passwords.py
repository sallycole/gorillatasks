
from app import db, create_app
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def fix_encrypted_passwords():
    """
    Ensure that encrypted_password is correctly set for all users.
    This will add the encrypted_password column if it doesn't exist
    and make sure it's correctly populated.
    """
    with app.app_context():
        try:
            # First check if encrypted_password column exists
            with db.engine.connect() as conn:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'users' AND column_name = 'encrypted_password'
                        ) THEN
                            ALTER TABLE users ADD COLUMN encrypted_password TEXT;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Ensured encrypted_password column exists")
                
                # Get all users with their current password information
                result = conn.execute(text("""
                    SELECT id, email, password_hash, encrypted_password
                    FROM users
                """))
                
                users = []
                for row in result:
                    user_id, email, password_hash, encrypted_password = row
                    users.append({
                        'id': user_id,
                        'email': email,
                        'password_hash': password_hash,
                        'encrypted_password': encrypted_password
                    })
                
                logger.info(f"Found {len(users)} users to process")
                
                # Process each user
                for user in users:
                    if not user['encrypted_password'] and user['password_hash']:
                        # If encrypted_password is missing but password_hash exists,
                        # copy password_hash to encrypted_password
                        conn.execute(text(f"""
                            UPDATE users 
                            SET encrypted_password = '{user['password_hash']}' 
                            WHERE id = {user['id']}
                        """))
                        logger.info(f"Copied password_hash to encrypted_password for user {user['id']} ({user['email']})")
                
                # Special case for phoebezcole@gmail.com - check if encrypted_password is correct
                result = conn.execute(text("""
                    SELECT id, email, encrypted_password FROM users 
                    WHERE email = 'phoebezcole@gmail.com'
                """))
                
                phoebe = result.fetchone()
                if phoebe:
                    logger.info(f"Found phoebezcole@gmail.com (ID: {phoebe[0]}) with encrypted_password: {phoebe[2]}")
                else:
                    logger.warning("User phoebezcole@gmail.com not found")
                
                conn.commit()
                logger.info("Password fix completed successfully")
                
        except Exception as e:
            logger.error(f"Error fixing passwords: {str(e)}")
            raise

if __name__ == "__main__":
    fix_encrypted_passwords()
