
from app import app, db
from models import Curriculum

with app.app_context():
    c = Curriculum.query.get(1)  # 2nd Grade Math has ID 1
    c.published = False
    db.session.commit()
    print(f'Updated curriculum {c.name} - Published status: {c.published}')
