
from app import db, app
from sqlalchemy import text

def run_migrations():
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE curriculums 
                ADD COLUMN IF NOT EXISTS public BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS locked BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE
            """))
            conn.commit()

if __name__ == "__main__":
    run_migrations()
