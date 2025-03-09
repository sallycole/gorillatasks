
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Check if column exists first
        result = conn.execute(text("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'password_hash'"))
        column_info = result.fetchone()
        
        if column_info:
            # Column exists, check if size needs to be increased
            if column_info[2] < 255:
                print(f"Updating password_hash column size from {column_info[2]} to 255")
                conn.execute(text('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255)'))
                conn.commit()
                print("Successfully updated password_hash column size in users table")
            else:
                print(f"password_hash column already has sufficient size: {column_info[2]}")
        else:
            # Add column if it doesn't exist
            conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)'))
            conn.commit()
            print("Successfully added password_hash column to users table")
