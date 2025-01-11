
from app import app, db
from models import Enrollment
from datetime import datetime
import pytz

def reset_all_weekly_goals():
    with app.app_context():
        try:
            enrollments = Enrollment.query.all()
            print(f"Found {len(enrollments)} enrollments")
            
            for enrollment in enrollments:
                old_goal = enrollment.weekly_goal_count
                # Force recalculation ignoring all completed tasks
                enrollment.weekly_goal_count = enrollment.calculate_weekly_goal(ignore_completed=True)
                db.session.add(enrollment)
                print(f"Enrollment {enrollment.id}: {old_goal} -> {enrollment.weekly_goal_count} tasks per week")
            
            # Explicitly flush and commit changes
            db.session.flush()
            db.session.commit()
            print("Weekly goals reset and saved to database")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    reset_all_weekly_goals()
