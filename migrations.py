
from app import db, app
from sqlalchemy import text

def run_migrations():
    with app.app_context():
        with db.engine.connect() as conn:
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
            conn.commit()

if __name__ == "__main__":
    run_migrations()
