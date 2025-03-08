
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add indexes to speed up common queries
        # Index for finding student tasks
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_student_tasks_student_id ON student_tasks (student_id)'))
        # Index for task curriculum
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_tasks_curriculum_id ON tasks (curriculum_id, position)'))
        # Index for student task status
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_student_tasks_status ON student_tasks (status)'))
        # Index for enrollments
        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_enrollments_student_id ON enrollments (student_id, paused)'))
        conn.commit()
    print("Successfully added performance optimization indexes")
