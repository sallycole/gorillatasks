
from app import app, db
from models import Curriculum, Task
from sqlalchemy import text

with app.app_context():
    # Add is_adaptive column to Curriculum if it doesn't exist
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE curriculums ADD COLUMN IF NOT EXISTS is_adaptive BOOLEAN DEFAULT FALSE"))
            conn.commit()
        print("Added is_adaptive column to Curriculum table")
    except Exception as e:
        print(f"Error adding is_adaptive to Curriculum: {e}")
    
    # Add is_adaptive column to Task if it doesn't exist
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_adaptive BOOLEAN DEFAULT FALSE"))
            conn.commit()
        print("Added is_adaptive column to Task table")
    except Exception as e:
        print(f"Error adding is_adaptive to Task: {e}")
    
    print("Migration completed successfully")
