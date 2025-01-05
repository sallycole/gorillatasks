
from app import app, db
from models import User

with app.app_context():
    print(f'Connected to database. Users count: {User.query.count()}')
