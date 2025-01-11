
from app import app, db
from models import Enrollment, StudentTask, Task
from datetime import datetime, timedelta
import pytz

def reset_all_weekly_goals():
    with app.app_context():
        try:
            enrollments = Enrollment.query.all()
            print(f"Found {len(enrollments)} enrollments")
            
            # Calculate Friday midnight in UTC
            utc_now = datetime.now(pytz.UTC)
            days_since_friday = (utc_now.weekday() - 4) % 7  # Friday is 4
            last_friday = utc_now - timedelta(days=days_since_friday)
            friday_midnight = last_friday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            for enrollment in enrollments:
                # Count tasks completed since Friday midnight
                completed_tasks = StudentTask.query.join(Task).filter(
                    StudentTask.student_id == enrollment.student_id,
                    Task.curriculum_id == enrollment.curriculum_id,
                    StudentTask.status == StudentTask.STATUS_COMPLETED,
                    StudentTask.finished_at >= friday_midnight
                ).count()
                
                # Calculate required weekly tasks based on target date
                total_tasks = len(enrollment.curriculum.tasks)
                if enrollment.target_completion_date:
                    remaining_weeks = ((enrollment.target_completion_date - utc_now.date()).days / 7)
                    remaining_weeks = max(1, int(remaining_weeks) + (1 if remaining_weeks > int(remaining_weeks) else 0))
                    weekly_goal = -(-total_tasks // remaining_weeks)  # Ceiling division
                else:
                    weekly_goal = 0
                    
                enrollment.weekly_goal_count = weekly_goal
                db.session.add(enrollment)
                print(f"Enrollment {enrollment.id}: {completed_tasks} completed this week, goal is {weekly_goal}")
            
            db.session.commit()
            print("Weekly goals recalculated and saved")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    reset_all_weekly_goals()
