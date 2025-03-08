
from app import db, create_app
from models import User
from werkzeug.security import generate_password_hash
import sys

app = create_app()

def reset_password(email, new_password):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"User with email {email} not found.")
            return False
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"Password reset successfully for {email}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    reset_password(email, new_password)
