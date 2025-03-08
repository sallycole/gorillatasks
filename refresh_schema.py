
from app import app, db
from sqlalchemy import text, inspect
from models import Task, Curriculum

with app.app_context():
    # Check if columns exist
    inspector = inspect(db.engine)
    
    print("Checking Task table columns...")
    task_columns = [col['name'] for col in inspector.get_columns('tasks')]
    print(f"Task columns: {task_columns}")
    print(f"is_adaptive in Task table: {'is_adaptive' in task_columns}")
    
    print("\nChecking Curriculum table columns...")
    curriculum_columns = [col['name'] for col in inspector.get_columns('curriculums')]
    print(f"Curriculum columns: {curriculum_columns}")
    print(f"is_adaptive in Curriculum table: {'is_adaptive' in curriculum_columns}")
    
    # Refresh SQLAlchemy metadata
    print("\nRefreshing SQLAlchemy metadata...")
    db.Model.metadata.reflect(db.engine)
    
    print("\nRestarting Flask application...")
