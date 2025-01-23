
from app import app, db

with app.app_context():
    db.engine.execute('ALTER TABLE tasks ALTER COLUMN link TYPE VARCHAR(1000)')
    print("Successfully updated link column length")
