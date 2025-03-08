
from app import app, db
from models import Curriculum, Task

with app.app_context():
    # Add is_adaptive column to Curriculum if it doesn't exist
    try:
        db.engine.execute("ALTER TABLE curriculums ADD COLUMN IF NOT EXISTS is_adaptive BOOLEAN DEFAULT FALSE")
        print("Added is_adaptive column to Curriculum table")
    except Exception as e:
        print(f"Error adding is_adaptive to Curriculum: {e}")
    
    # Add is_adaptive column to Task if it doesn't exist
    try:
        db.engine.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_adaptive BOOLEAN DEFAULT FALSE")
        print("Added is_adaptive column to Task table")
    except Exception as e:
        print(f"Error adding is_adaptive to Task: {e}")
    
    print("Migration completed successfully")
