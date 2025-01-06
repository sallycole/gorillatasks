
from app import app, db
from models import Curriculum

with app.app_context():
    c = Curriculum.query.get(1)  # 2nd Grade Math has ID 1
    c.published = False
    c.locked = False
    db.session.commit()
    print(f'Updated curriculum {c.name} - Published: {c.published}, Locked: {c.locked}')
