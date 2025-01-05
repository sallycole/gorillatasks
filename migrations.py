
from app import db

def run_migrations():
    with db.engine.connect() as conn:
        conn.execute("""
            ALTER TABLE curriculums 
            ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS locked BOOLEAN DEFAULT FALSE
        """)
        conn.commit()

if __name__ == "__main__":
    run_migrations()
