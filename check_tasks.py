
from app import app, db
from models import Task, Curriculum

with app.app_context():
    orphaned_tasks = Task.query.filter(
        ~Task.curriculum_id.in_(
            db.session.query(Curriculum.id)
        )
    ).all()
    
    print("\nOrphaned Tasks (tasks without curriculums):")
    print("-" * 50)
    for task in orphaned_tasks:
        print(f"Task ID: {task.id}")
        print(f"Title: {task.title}")
        print(f"Curriculum ID: {task.curriculum_id}")
        print("-" * 50)
