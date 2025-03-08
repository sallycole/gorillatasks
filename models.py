from flask_login import UserMixin, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import enum
from datetime import datetime, timedelta, date
import pytz
import uuid
import random

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(255))  # Increased size to handle longer hashes
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_superuser = db.Column(db.Boolean, default=False)
    time_zone = db.Column(db.String(50), default='UTC')

    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic', cascade="all, delete-orphan")
    tasks = db.relationship('StudentTask', backref='student', lazy='dynamic', cascade="all, delete-orphan")
    profile = db.relationship('Profile', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        import logging
        logger = logging.getLogger(__name__)

        if not password:
            logger.warning(f"Empty password provided for user {self.id}")
            return False

        # Handle the case where password_hash is None or doesn't exist
        if self.password_hash is None or not self.password_hash:
            logger.warning(f"No password hash found for user {self.id}")

            # Check the encrypted_password field (used by some legacy systems)
            if hasattr(self, 'encrypted_password') and self.encrypted_password:
                logger.info(f"Checking encrypted_password for user {self.id}")
                # Try direct comparison with encrypted_password (could be plain text or already hashed)
                if self.encrypted_password == password:
                    logger.info(f"Direct encrypted_password match for user {self.id}")
                    # Migrate to the new password_hash format
                    self.set_password(password)
                    from app import db
                    db.session.commit()
                    return True
                # Also try if encrypted_password is already in hash format
                elif self.encrypted_password.startswith('pbkdf2:sha256:') and check_password_hash(self.encrypted_password, password):
                    logger.info(f"Hashed encrypted_password match for user {self.id}")
                    # Move the hash to password_hash
                    self.password_hash = self.encrypted_password
                    from app import db
                    db.session.commit()
                    return True

            # Legacy check: directly compare with the password for backward compatibility
            if hasattr(self, 'password') and self.password == password:
                logger.info(f"Legacy password match for user {self.id}")
                # Update to the new hash format if legacy match succeeds
                self.set_password(password)
                from app import db
                db.session.commit()
                return True

            return False

        # Handle plain-text passwords stored in password_hash field
        if not self.password_hash.startswith('pbkdf2:sha256:'):
            logger.warning(f"Password in non-hashed format for user {self.id}")
            # Check if the plain-text password matches
            if self.password_hash == password:
                logger.info(f"Plain-text password match for user {self.id}")
                # Update to the new hash format if plain-text match succeeds
                self.password_hash = generate_password_hash(password, method='sha256')
                from app import db
                db.session.commit()
                return True
            return False

        # Normal case: verify using werkzeug's check_password_hash
        try:
            result = check_password_hash(self.password_hash, password)
            logger.info(f"Password check for user {self.id}: {'success' if result else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Error in password verification for user {self.id}: {str(e)}")
            # Last resort: try direct comparison for legacy compatibility
            if self.password_hash == password:
                logger.info(f"Direct password match after hash check failure for user {self.id}")
                # Update to the new hash format
                self.password_hash = generate_password_hash(password, method='sha256')
                from app import db
                db.session.commit()
                return True
            return False

    def __repr__(self):
        return f'<User {self.username}>'

    def get_timezone(self):
        try:
            return pytz.timezone(self.time_zone)
        except:
            return pytz.UTC

class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    school = db.Column(db.String(100), nullable=True)
    grade_level = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Profile {self.user_id}>'

# Grade levels for dropdown menus
GRADE_LEVELS = [
    'Pre-K', 'Kindergarten', 
    '1st Grade', '2nd Grade', '3rd Grade', '4th Grade', '5th Grade',
    '6th Grade', '7th Grade', '8th Grade', 
    '9th Grade', '10th Grade', '11th Grade', '12th Grade',
    'College', 'Adult'
]

class Curriculum(db.Model):
    __tablename__ = 'curriculums'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(2048), nullable=True)
    public = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    publisher = db.Column(db.String(100), nullable=True)
    grade_levels = db.Column(db.ARRAY(db.String), default=list)
    is_adaptive = db.Column(db.Boolean, default=False)

    # Define the relationship to User
    creator = db.relationship('User', backref=db.backref('created_curriculums', lazy='dynamic'))

    # Define one-to-many relationship with tasks
    tasks = db.relationship('Task', backref='curriculum', lazy='dynamic', cascade="all, delete-orphan", 
                           order_by="Task.position")

    # Define many-to-many relationship with students through enrollments
    enrollments = db.relationship('Enrollment', backref='curriculum', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Curriculum {self.name}>'

    def get_active_enrollment(self, user_id):
        return Enrollment.query.filter_by(
            curriculum_id=self.id, 
            student_id=user_id,
            paused=False
        ).first()

    def get_enrollment(self, user_id):
        return Enrollment.query.filter_by(
            curriculum_id=self.id, 
            student_id=user_id
        ).first()

    def is_enrolled(self, user_id):
        return db.session.query(Enrollment).filter(
            Enrollment.curriculum_id == self.id,
            Enrollment.student_id == user_id
        ).first() is not None

class Task(db.Model):
    __tablename__ = 'tasks'

    # Action type constants
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
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, default=0)
    link = db.Column(db.String(2048), nullable=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id', ondelete='CASCADE'))
    action = db.Column(db.Integer, default=0)  # 0=None, 1=Read, 2=Watch, 3=Listen, 4=Do
    is_adaptive = db.Column(db.Boolean, default=False)

    # Define relationship with StudentTask
    student_tasks = db.relationship('StudentTask', backref='task', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Task {self.title}>'

class StudentTask(db.Model):
    __tablename__ = 'student_tasks'

    # Status constants
    STATUS_NOT_STARTED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_COMPLETED = 2
    STATUS_SKIPPED = 3

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'))
    status = db.Column(db.Integer, default=STATUS_NOT_STARTED)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    skipped_at = db.Column(db.DateTime, nullable=True)
    time_spent_minutes = db.Column(db.Integer, default=0)
    promoted = db.Column(db.Boolean, default=False)

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED

    @property
    def is_started(self):
        return self.status in [self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED]

    @property
    def can_start(self):
        return self.status == self.STATUS_NOT_STARTED

    @property
    def can_finish(self):
        return self.status == self.STATUS_IN_PROGRESS

    @property
    def can_skip(self):
        return self.status != self.STATUS_COMPLETED

    def start(self):
        self.status = self.STATUS_IN_PROGRESS
        self.started_at = datetime.now(pytz.UTC)

    def finish(self):
        self.status = self.STATUS_COMPLETED
        self.finished_at = datetime.now(pytz.UTC)
        if self.started_at:
            started_at_utc = pytz.UTC.localize(self.started_at) if self.started_at.tzinfo is None else self.started_at.astimezone(pytz.UTC)
            delta = self.finished_at - started_at_utc
            self.time_spent_minutes = int(delta.total_seconds() / 60)

    def skip(self):
        if self.status != self.STATUS_COMPLETED:
            self.status = self.STATUS_SKIPPED
            self.skipped_at = datetime.now(pytz.UTC)

    def __repr__(self):
        return f'<StudentTask {self.student_id}-{self.task_id}>'

class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curriculums.id', ondelete='CASCADE'))
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    daily_goal_count = db.Column(db.Integer, default=1)
    weekly_goal_count = db.Column(db.Integer, default=5)
    study_days_per_week = db.Column(db.Integer, default=5)
    target_completion_date = db.Column(db.Date, nullable=True)
    paused = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Enrollment {self.student_id}-{self.curriculum_id}>'

    def is_completed(self):
        if not self.curriculum:
            return False

        # For adaptive curriculums, only consider them complete if target date has passed
        if self.curriculum.is_adaptive:
            if not self.target_completion_date:
                return False

            from datetime import datetime
            import pytz
            current_date = datetime.now(pytz.UTC).date()
            return current_date > self.target_completion_date

        # For regular curriculums, check if all tasks are completed
        total_tasks = len(self.curriculum.tasks.all())
        if total_tasks == 0:
            return False

        completed_tasks = StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.status.in_([StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED])
        ).count()

        return completed_tasks >= total_tasks

    def tasks_completed(self):
        if not self.curriculum:
            return 0

        return StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.status.in_([StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED])
        ).count()

    def tasks_completed_today(self):
        if not self.curriculum:
            return 0

        # Get user's timezone
        tz = current_user.get_timezone()
        now = datetime.now(tz)
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
        today_end = today_start + timedelta(days=1)

        # Convert to UTC for database query
        today_start_utc = today_start.astimezone(pytz.UTC)
        today_end_utc = today_end.astimezone(pytz.UTC)

        return StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.status == StudentTask.STATUS_COMPLETED,
            StudentTask.finished_at >= today_start_utc,
            StudentTask.finished_at < today_end_utc
        ).count()

    def tasks_completed_this_week(self):
        if not self.curriculum:
            return 0

        # Get user's timezone
        tz = current_user.get_timezone()
        now = datetime.now(tz)

        # Calculate the start of the current week (Monday)
        week_start = now - timedelta(days=now.weekday())
        week_start = datetime(week_start.year, week_start.month, week_start.day, 0, 0, 0, tzinfo=tz)
        week_end = week_start + timedelta(days=7)

        # Convert to UTC for database query
        week_start_utc = week_start.astimezone(pytz.UTC)
        week_end_utc = week_end.astimezone(pytz.UTC)

        return StudentTask.query.join(Task).filter(
            StudentTask.student_id == self.student_id,
            Task.curriculum_id == self.curriculum_id,
            StudentTask.status == StudentTask.STATUS_COMPLETED,
            StudentTask.finished_at >= week_start_utc,
            StudentTask.finished_at < week_end_utc
        ).count()

    def calculate_weekly_goal(self):
        """Calculate weekly goal based on target completion and remaining tasks"""
        if not self.target_completion_date or not self.curriculum:
            return self.weekly_goal_count

        today = date.today()

        # If target date has passed, no weekly goal
        if today >= self.target_completion_date:
            return 0

        # For adaptive curriculums, just use the days per week setting
        if self.curriculum.is_adaptive:
            return self.study_days_per_week

        # Calculate weeks remaining
        days_remaining = (self.target_completion_date - today).days
        weeks_remaining = max(1, days_remaining / 7)

        # Calculate tasks remaining
        total_tasks = len(self.curriculum.tasks.all())
        completed_tasks = self.tasks_completed()
        tasks_remaining = max(0, total_tasks - completed_tasks)

        # If no tasks remaining, no weekly goal
        if tasks_remaining == 0:
            return 0

        # Calculate weekly goal
        weekly_goal = int(tasks_remaining / weeks_remaining)

        # Ensure at least 1 task per week if there are tasks remaining
        return max(1, weekly_goal)

    def calculate_todays_goal(self):
        if not self.target_completion_date:
            return self.daily_goal_count

        # Get user's timezone
        tz = current_user.get_timezone()
        today = datetime.now(tz).date()

        if today >= self.target_completion_date:
            # Target date has passed
            return 0

        # Calculate days remaining
        days_remaining = (self.target_completion_date - today).days
        if days_remaining <= 0:
            return 0

        # Calculate tasks remaining
        if self.curriculum.is_adaptive:
            # For adaptive curricula, we don't have a fixed number of tasks
            # So just use the daily goal
            return self.daily_goal_count

        tasks_remaining = len(self.curriculum.tasks.all()) - self.tasks_completed()
        if tasks_remaining <= 0:
            return 0

        # Calculate adjusted daily goal
        adjusted_goal = max(1, tasks_remaining // days_remaining)

        # Cap at daily_goal_count if specified
        if self.daily_goal_count > 0:
            adjusted_goal = min(adjusted_goal, self.daily_goal_count)

        return adjusted_goal

    def progress_status(self, completed, goal):
        if goal <= 0:
            return "text-muted"

        ratio = completed / goal
        if ratio >= 1:
            return "progress-complete"
        elif ratio >= 0.5:
            return "progress-partial"
        else:
            return "progress-none"

    def target_date_status(self):
        if not self.target_completion_date:
            return "text-muted"

        today = date.today()
        days_remaining = (self.target_completion_date - today).days

        if self.is_completed():
            return "progress-complete"
        elif days_remaining < 0:
            return "progress-none"  # Overdue
        elif days_remaining <= 7:
            return "progress-partial"  # Less than a week
        else:
            return "text-muted"  # More than a week

class WeeklySnapshot(db.Model):
    __tablename__ = 'weekly_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    week_starting = db.Column(db.Date, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)
    time_spent_minutes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WeeklySnapshot {self.user_id}-{self.week_starting}>'

# Function to generate a random UUID token
def generate_token():
    return str(uuid.uuid4())