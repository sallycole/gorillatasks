
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add password_hash column if it doesn't exist
        conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128)'))
        conn.commit()
    print("Successfully added password_hash column to users table")
