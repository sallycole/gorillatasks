
from app import app, db
from models import StudentTask
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_promoted():
    try:
        with app.app_context():
            # Check if 'promoted' column exists
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('student_tasks')]
            
            if 'promoted' not in columns:
                logger.info("Adding 'promoted' column to student_tasks table...")
                db.engine.execute('ALTER TABLE student_tasks ADD COLUMN promoted BOOLEAN DEFAULT FALSE')
                logger.info("Successfully added 'promoted' column!")
            else:
                logger.info("'promoted' column already exists!")
                
            logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        
if __name__ == "__main__":
    migrate_add_promoted()
