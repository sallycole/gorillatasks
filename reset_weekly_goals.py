
from app import app, db
from models import Enrollment

def reset_all_weekly_goals():
    with app.app_context():
        enrollments = Enrollment.query.all()
        print(f"Found {len(enrollments)} enrollments")
        
        for enrollment in enrollments:
            old_goal = enrollment.weekly_goal_count
            new_goal = enrollment.recalculate_weekly_goal()
            print(f"Enrollment {enrollment.id}: {old_goal} -> {new_goal} tasks per week")
        
        print("Weekly goals recalculated for all enrollments")

if __name__ == "__main__":
    reset_all_weekly_goals()
