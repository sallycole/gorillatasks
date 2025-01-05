
from app import app, db
from models import User, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot

def reset_database():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("Dropped all tables")
        
        # Recreate tables
        db.create_all()
        print("Recreated all tables")
        
        print("Database has been reset successfully")

if __name__ == "__main__":
    reset_database()
