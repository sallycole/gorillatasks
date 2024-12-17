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
    
    # Status Constants
    STATUS_NOT_STARTED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_COMPLETED = 2
    STATUS_SKIPPED = 3
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    status = db.Column(db.Integer, default=STATUS_NOT_STARTED)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    skipped_at = db.Column(db.DateTime)
    time_spent_minutes = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def can_start(self):
        # Can only start if no other task is in progress and this task isn't completed or skipped
        return (self.status == self.STATUS_NOT_STARTED and 
                not StudentTask.query.filter_by(
                    student_id=self.student_id,
                    status=self.STATUS_IN_PROGRESS
                ).first())
    
    @property
    def can_finish(self):
        return self.status == self.STATUS_IN_PROGRESS
        
    @property
    def can_skip(self):
        return self.status in [self.STATUS_NOT_STARTED, self.STATUS_IN_PROGRESS]

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
    curriculum = db.relationship('Curriculum', backref='enrollments')
    student_tasks = db.relationship('StudentTask', secondary='tasks',
                                  primaryjoin='and_(Enrollment.curriculum_id==Task.curriculum_id, '
                                            'Enrollment.student_id==StudentTask.student_id)',
                                  secondaryjoin='Task.id==StudentTask.task_id',
                                  viewonly=True)

    def calculate_weekly_goal(self):
        if not self.target_completion_date:
            return 0
            
        total_tasks = len(self.curriculum.tasks)
        completed_tasks = StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            StudentTask.status == 2,  # Completed status
            Task.curriculum_id == self.curriculum_id
        ).count()
        
        remaining_tasks = total_tasks - completed_tasks
        current_date = datetime.now(pytz.UTC).date()
        weeks_remaining = ((self.target_completion_date - current_date).days / 7)
        weeks_remaining = int(weeks_remaining) + (1 if weeks_remaining > int(weeks_remaining) else 0)
        
        if weeks_remaining <= 0:
            return 0
            
        return int((remaining_tasks / weeks_remaining) + 0.5)  # Equivalent to ceil in Ruby

    def calculate_daily_divisor(self):
        current_day = datetime.now(pytz.UTC).strftime('%A')
        max_possible_days = {
            'Saturday': 7,
            'Sunday': 6,
            'Monday': 5,
            'Tuesday': 4,
            'Wednesday': 3,
            'Thursday': 2,
            'Friday': 1
        }.get(current_day, 7)
        
        return min(max_possible_days, self.study_days_per_week)

    def tasks_completed_this_week(self):
        week_start = datetime.now(pytz.UTC).date() - timedelta(days=datetime.now(pytz.UTC).weekday())
        return StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            StudentTask.status == 2,  # Completed status
            Task.curriculum_id == self.curriculum_id,
            StudentTask.updated_at >= week_start
        ).count()

    def calculate_todays_goal(self):
        if not self.weekly_goal_count:
            self.weekly_goal_count = self.calculate_weekly_goal()
            db.session.commit()
            
        daily_goal = int((self.weekly_goal_count / self.calculate_daily_divisor()) + 0.5)  # Equivalent to ceil
        remaining_weekly_tasks = self.weekly_goal_count - self.tasks_completed_this_week()
        return max(daily_goal, remaining_weekly_tasks, 0)

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
