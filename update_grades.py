
from app import app, db
from models import Curriculum

with app.app_context():
    c = Curriculum.query.get(1)
    c.grade_levels = ['2']
    db.session.commit()
    print(f'Updated curriculum {c.name} with grade levels: {c.grade_levels}')
