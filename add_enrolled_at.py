
from app import app, db
from sqlalchemy import text
from datetime import datetime

with app.app_context():
    with db.engine.connect() as conn:
        # Add enrolled_at column if it doesn't exist
        conn.execute(text('ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP'))
        conn.commit()
    print("Successfully added enrolled_at column to enrollments table")
