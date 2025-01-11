
from app import app, db
from models import Enrollment

def reset_all_weekly_goals():
    with app.app_context():
        # Start a database transaction
        try:
            enrollments = Enrollment.query.all()
            print(f"Found {len(enrollments)} enrollments")
            
            for enrollment in enrollments:
                old_goal = enrollment.weekly_goal_count
                new_goal = enrollment.calculate_weekly_goal(ignore_completed=True)
                enrollment.weekly_goal_count = new_goal
                db.session.add(enrollment)
                print(f"Enrollment {enrollment.id}: {old_goal} -> {new_goal} tasks per week")
            
            # Explicitly commit the transaction
            db.session.commit()
            print("Weekly goals recalculated and saved to database")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    reset_all_weekly_goals()
