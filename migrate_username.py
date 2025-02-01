
from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add username column
        conn.execute(text('ALTER TABLE users ADD COLUMN username VARCHAR(64) UNIQUE'))
        # Set existing users' usernames to their email addresses
        conn.execute(text('UPDATE users SET username = email'))
        conn.commit()
    print("Successfully added username column")
