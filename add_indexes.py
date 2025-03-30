
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add indexes to speed up common queries
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS idx_student_tasks_composite 
            ON student_tasks (student_id, task_id, status);
            
            CREATE INDEX IF NOT EXISTS idx_tasks_curriculum_id 
            ON tasks (curriculum_id, position);
            
            CREATE INDEX IF NOT EXISTS idx_enrollments_student 
            ON enrollments (student_id, paused);
            
            CREATE INDEX IF NOT EXISTS idx_curriculum_adaptive 
            ON curriculums (is_adaptive) 
            WHERE is_adaptive = true;
            
            CREATE INDEX IF NOT EXISTS idx_student_tasks_status 
            ON student_tasks (status, student_id, finished_at);
        '''))
        conn.commit()
    print("Successfully added performance optimization indexes")
