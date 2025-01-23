
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text('ALTER TABLE tasks ALTER COLUMN link TYPE VARCHAR(1000)'))
        conn.commit()
    print("Successfully updated link column length")
