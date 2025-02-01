
from app import app, db
from sqlalchemy import text

def add_superuser_column():
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE'))
            conn.commit()
        print('Added is_superuser column')

if __name__ == "__main__":
    add_superuser_column()
