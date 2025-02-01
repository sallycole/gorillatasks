
from app import app, db

def add_superuser_column():
    with app.app_context():
        db.engine.execute('ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE')
        print('Added is_superuser column')

if __name__ == "__main__":
    add_superuser_column()
