
from app import app, db
from models import Curriculum

with app.app_context():
    c = Curriculum.query.get(1)  # 2nd Grade Math has ID 1
    c.published = False
    c.locked = False
    db.session.commit()
    print(f'Updated curriculum {c.name} - Published: {c.published}, Locked: {c.locked}')
from app import app, db
from models import Curriculum

with app.app_context():
    # Look up curriculum by name
    c = Curriculum.query.filter(
        Curriculum.name.ilike('Paws for a Minute - Watch and Read About Animals')
    ).first()
    
    if c:
        c.published = False
        c.locked = False
        db.session.commit()
        print(f'Updated curriculum {c.name} - Published: {c.published}, Locked: {c.locked}')
    else:
        print('Curriculum not found')
