from app import db, app
from sqlalchemy import text

def run_migrations():
    with app.app_context():
        with db.engine.connect() as conn:
            # Backup existing data
            conn.execute(text("CREATE TEMP TABLE curriculum_backup AS SELECT * FROM curriculums"))
            
            # Drop existing table
            conn.execute(text("DROP TABLE IF EXISTS curriculums CASCADE"))
            
            # Create new table with all columns
            conn.execute(text("""
                CREATE TABLE curriculums (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    description TEXT,
                    link VARCHAR(255),
                    public BOOLEAN DEFAULT FALSE,
                    published BOOLEAN DEFAULT FALSE,
                    locked BOOLEAN DEFAULT FALSE,
                    creator_id INTEGER REFERENCES users(id),
                    publisher VARCHAR(255),
                    published_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    grade_levels VARCHAR(255)[]
                )
            """))
            
            # Restore data
            conn.execute(text("""
                INSERT INTO curriculums (id, name, description, link, public, published, 
                    locked, creator_id, publisher, published_at, created_at, updated_at)
                SELECT id, name, description, link, public, published,
                    locked, creator_id, publisher, published_at, created_at, updated_at
                FROM curriculum_backup
            """))
            
            # Reset sequence
            conn.execute(text("SELECT setval('curriculums_id_seq', (SELECT MAX(id) FROM curriculums))"))
            conn.commit()

if __name__ == "__main__":
    run_migrations()