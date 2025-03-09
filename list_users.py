
from app import app, db
from models import User
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_all_users():
    with app.app_context():
        users = User.query.all()
        
        print(f"Total users: {len(users)}")
        print("-" * 80)
        print(f"{'ID':<5} {'Email':<30} {'Name':<30} {'Is Superuser':<15} {'Is Active':<10}")
        print("-" * 80)
        
        for user in users:
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            print(f"{user.id:<5} {user.email:<30} {full_name:<30} {str(user.is_superuser):<15} {str(user.is_active):<10}")

if __name__ == "__main__":
    list_all_users()
