from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from utils.timezone import now_in_utc, to_user_timezone, from_user_timezone

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
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)
    
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
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)

class Curriculum(db.Model):
    __tablename__ = 'curriculums'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    link = db.Column(db.String(255))
    public = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    publisher = db.Column(db.String(255))
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)
    
    tasks = db.relationship('Task', backref='curriculum', 
                          cascade='all, delete-orphan', 
                          passive_deletes=True)
    grade_levels = db.Column(db.ARRAY(db.String(255)), default=list)

# Constants for grade levels
GRADE_LEVELS = [
    ('K', 'Kindergarten'),
    ('1', '1st Grade'),
    ('2', '2nd Grade'),
    ('3', '3rd Grade'),
    ('4', '4th Grade'),
    ('5', '5th Grade'),
    ('6', '6th Grade'),
    ('7', '7th Grade'),
    ('8', '8th Grade'),
    ('9', '9th Grade'),
    ('10', '10th Grade'),
    ('11', '11th Grade'),
    ('12', '12th Grade'),
    ('College', 'College')
]

class Task(db.Model):
    __tablename__ = 'tasks'
    
    ACTION_READ = 1
    ACTION_WATCH = 2
    ACTION_LISTEN = 3
    ACTION_DO = 4

    ACTION_MAP = {
        'Read': ACTION_READ,
        'Watch': ACTION_WATCH,
        'Listen': ACTION_LISTEN,
        'Do': ACTION_DO
    }

    ACTION_MAP_REVERSE = {
        ACTION_READ: 'Read',
        ACTION_WATCH: 'Watch',
        ACTION_LISTEN: 'Listen',
        ACTION_DO: 'Do'
    }

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=False)
    link = db.Column(db.String(255))
    action = db.Column(db.Integer)
    position = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)

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
    task = db.relationship('Task', backref='student_tasks', lazy='joined')
    status = db.Column(db.Integer, default=STATUS_NOT_STARTED)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    skipped_at = db.Column(db.DateTime)
    time_spent_minutes = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)
    
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
        
    def start(self):
        self.status = self.STATUS_IN_PROGRESS
        self.started_at = now_in_utc()
        self.finished_at = None
        self.skipped_at = None
        self.time_spent_minutes = 0
        
    def finish(self):
        if self.started_at:
            self.finished_at = now_in_utc()
            self.status = self.STATUS_COMPLETED
            delta = self.finished_at - self.started_at
            self.time_spent_minutes = int(delta.total_seconds() / 60)
            
    def skip(self):
        self.status = self.STATUS_SKIPPED
        self.skipped_at = now_in_utc()
        self.started_at = None
        self.finished_at = None
        self.time_spent_minutes = 0

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    def is_completed(self):
        if not self.curriculum:
            return False
        total_tasks = len(self.curriculum.tasks)
        if total_tasks == 0:
            return False
            
        completed_count = StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.status.in_([StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED])
        ).count()
        
        return completed_count == total_tasks
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id'), nullable=False)
    weekly_goal_count = db.Column(db.Integer, default=5, nullable=False)
    study_days_per_week = db.Column(db.Integer)
    target_completion_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)
    
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

    def get_weekday_value(self):
        from flask_login import current_user
        from utils.timezone import to_user_timezone
        current_time = datetime.now(pytz.UTC)
        user_time = to_user_timezone(current_time, current_user)
        current_day = user_time.strftime('%A')
        return {
            'Monday': 5,
            'Tuesday': 4,
            'Wednesday': 3,
            'Thursday': 2,
            'Friday': 1,
            'Saturday': 7,
            'Sunday': 6
        }.get(current_day, 0)
        
    def get_remaining_study_days(self):
        if not self.study_days_per_week:
            return 0
            
        remaining_days = self.get_weekday_value()
        return min(remaining_days, self.study_days_per_week)
        
    def calculate_daily_divisor(self):
        return self.get_remaining_study_days()

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
            
        # Check tasks already completed this week
        tasks_done = self.tasks_completed_this_week()
        remaining_tasks = max(0, self.weekly_goal_count - tasks_done)
        
        # If weekly goal is met or exceeded, no tasks needed today
        if remaining_tasks == 0:
            return 0
            
        remaining_study_days = self.get_remaining_study_days()
        if remaining_study_days == 0:
            return 0
            
        # Daily goal is remaining tasks divided by remaining study days
        return -(-remaining_tasks // remaining_study_days)  # Ceiling division

    def tasks_completed_today(self):
        today_start = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            StudentTask.status == StudentTask.STATUS_COMPLETED,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.updated_at >= today_start
        ).count()
        
    @staticmethod
    def progress_status(completed, goal):
        if goal == 0:
            return 'progress-complete'
        elif completed == 0:
            return 'progress-none'
        elif completed < goal:
            return 'progress-partial'
        else:
            return 'progress-complete'

class WeeklySnapshot(db.Model):
    __tablename__ = 'weekly_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    tasks_completed = db.Column(db.Integer)
    weekly_goal = db.Column(db.Integer)
    week_ending = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=now_in_utc)
    updated_at = db.Column(db.DateTime, default=now_in_utc, onupdate=now_in_utc)