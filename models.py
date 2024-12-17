from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    encrypted_password = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    time_zone = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    profile = db.relationship('Profile', backref='user', uselist=False)
    created_curriculums = db.relationship('Curriculum', backref='creator')
    
    def set_password(self, password):
        self.encrypted_password = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.encrypted_password, password)

class Profile(db.Model):
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Curriculum(db.Model):
    __tablename__ = 'curriculums'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    link = db.Column(db.String(255))
    public = db.Column(db.Boolean, default=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    publisher = db.Column(db.String(255))
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='curriculum', cascade='all, delete-orphan')
    grade_levels = db.relationship('GradeLevel', secondary='curriculum_grade_levels')

class GradeLevel(db.Model):
    __tablename__ = 'grade_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CurriculumGradeLevel(db.Model):
    __tablename__ = 'curriculum_grade_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=False)
    grade_level_id = db.Column(db.Integer, db.ForeignKey('grade_levels.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=False)
    link = db.Column(db.String(255))
    action = db.Column(db.Integer)
    position = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StudentTask(db.Model):
    __tablename__ = 'student_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    status = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    skipped_at = db.Column(db.DateTime)
    time_spent_minutes = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=False)
    weekly_goal_count = db.Column(db.Integer, default=5, nullable=False)
    study_days_per_week = db.Column(db.Integer)
    target_completion_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    weekly_snapshots = db.relationship('WeeklySnapshot', backref='enrollment')

class WeeklySnapshot(db.Model):
    __tablename__ = 'weekly_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    tasks_completed = db.Column(db.Integer)
    weekly_goal = db.Column(db.Integer)
    week_ending = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
