
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add indexes to speed up common queries
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS idx_student_tasks_composite 
            ON student_tasks (student_id, task_id, status);
            
            CREATE INDEX IF NOT EXISTS idx_tasks_curriculum_composite 
            ON tasks (curriculum_id, position, is_adaptive);
            
            CREATE INDEX IF NOT EXISTS idx_enrollments_composite 
            ON enrollments (student_id, curriculum_id, paused);
            
            CREATE INDEX IF NOT EXISTS idx_student_tasks_promoted 
            ON student_tasks (promoted) 
            WHERE promoted = true;
        '''))
        conn.commit()
    print("Successfully added performance optimization indexes")
