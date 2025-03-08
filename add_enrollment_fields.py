from app import app, db
from sqlalchemy import text
from datetime import datetime

with app.app_context():
    with db.engine.connect() as conn:
        # Add all missing enrollment columns
        conn.execute(text('ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS daily_goal_count INTEGER DEFAULT 1'))
        conn.execute(text('ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS weekly_goal_count INTEGER DEFAULT 5'))
        conn.execute(text('ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS study_days_per_week INTEGER DEFAULT 5'))
        conn.execute(text('ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS target_completion_date DATE'))
        conn.commit()
    print("Successfully added missing columns to enrollments table")