
from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(email='sallycole@gmail.com').first()
    if user:
        user.is_superuser = True
        db.session.commit()
        print('Superuser status updated')
    else:
        print('User not found')
