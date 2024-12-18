
import unittest
from datetime import datetime
from app import create_app, db
from models import User, Task, StudentTask, Curriculum
import pytz

class TestTaskActions(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Create test user
        self.user = User(email='test@test.com')
        self.user.set_password('test123')
        db.session.add(self.user)
        
        # Create test curriculum and task
        self.curriculum = Curriculum(name='Test Curriculum')
        db.session.add(self.curriculum)
        db.session.commit()
        
        self.task = Task(
            title='Test Task',
            curriculum_id=self.curriculum.id,
            link='http://test.com'
        )
        db.session.add(self.task)
        db.session.commit()

    def test_start_task(self):
        with self.client:
            # Login
            self.client.post('/auth/login', data={
                'email': 'test@test.com',
                'password': 'test123'
            })
            
            # Start task
            before_time = datetime.now(pytz.UTC)
            response = self.client.post(f'/dashboard/task/{self.task.id}/start')
            after_time = datetime.now(pytz.UTC)
            
            # Get updated student task
            student_task = StudentTask.query.filter_by(
                student_id=self.user.id,
                task_id=self.task.id
            ).first()
            
            # Verify response and state changes
            self.assertEqual(response.status_code, 200)
            self.assertEqual(student_task.status, StudentTask.STATUS_IN_PROGRESS)
            self.assertIsNotNone(student_task.started_at)
            self.assertTrue(before_time <= student_task.started_at <= after_time)
            
            # Verify response includes task URL
            response_data = response.get_json()
            self.assertEqual(response_data['task']['link'], self.task.link)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

if __name__ == '__main__':
    unittest.main()
