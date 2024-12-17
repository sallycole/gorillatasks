from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm
from datetime import datetime, timedelta
import pytz

# Blueprint registration
auth_bp = Blueprint('auth', __name__)
curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')
dashboard_bp = Blueprint('dashboard', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard.index'))
        flash('Invalid email or password')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            time_zone=form.time_zone.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Dashboard routes
@dashboard_bp.route('/')
@login_required
def index():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Get weekly snapshots for the past 4 weeks
    four_weeks_ago = datetime.now(pytz.UTC) - timedelta(weeks=4)
    snapshots = WeeklySnapshot.query.filter(
        WeeklySnapshot.student_id == current_user.id,
        WeeklySnapshot.created_at >= four_weeks_ago
    ).order_by(WeeklySnapshot.week_ending.desc()).all()
    
    return render_template('dashboard/student.html', 
                         enrollments=enrollments,
                         snapshots=snapshots)

@dashboard_bp.route('/toggle_task/<int:id>', methods=['POST'])
@login_required
def toggle_task(id):
    task = Task.query.get_or_404(id)
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=task.id
    ).first()
    
    if not student_task:
        student_task = StudentTask(
            student_id=current_user.id,
            task_id=task.id,
            status=1
        )
        db.session.add(student_task)
    else:
        # Toggle between completed (2) and not started (0)
        student_task.status = 2 if student_task.status != 2 else 0
        
    db.session.commit()
    return redirect(url_for('dashboard.index'))

# Curriculum routes
@curriculum_bp.route('/')
@login_required
def list():
    curriculums = Curriculum.query.all()
    return render_template('curriculum/list.html', curriculums=curriculums)

@curriculum_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = CurriculumForm()
    if form.validate_on_submit():
        curriculum = Curriculum(
            name=form.name.data,
            description=form.description.data,
            link=form.link.data,
            public=form.public.data,
            creator_id=current_user.id,
            publisher=form.publisher.data
        )
        db.session.add(curriculum)
        db.session.commit()
        flash('Curriculum created successfully!')
        return redirect(url_for('curriculum.list'))
    return render_template('curriculum/edit.html', form=form)

@curriculum_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    curriculum = Curriculum.query.get_or_404(id)
    if curriculum.creator_id != current_user.id:
        flash('You can only edit your own curriculums')
        return redirect(url_for('curriculum.list'))
    
    form = CurriculumForm(obj=curriculum)
    if form.validate_on_submit():
        curriculum.name = form.name.data
        curriculum.description = form.description.data
        curriculum.link = form.link.data
        curriculum.public = form.public.data
        curriculum.publisher = form.publisher.data
        db.session.commit()
        flash('Curriculum updated successfully!')
        return redirect(url_for('curriculum.list'))
    return render_template('curriculum/edit.html', form=form, curriculum=curriculum)

@curriculum_bp.route('/<int:id>/enroll', methods=['GET', 'POST'])
@login_required
def enroll(id):
    curriculum = Curriculum.query.get_or_404(id)
    form = EnrollmentForm()
    
    if form.validate_on_submit():
        enrollment = Enrollment(
            student_id=current_user.id,
            curriculum_id=curriculum.id,
            weekly_goal_count=form.weekly_goal_count.data,
            study_days_per_week=form.study_days_per_week.data,
            target_completion_date=form.target_completion_date.data
        )
        
        # Create StudentTask entries for each task
        for task in curriculum.tasks:
            student_task = StudentTask(
                student_id=current_user.id,
                task_id=task.id,
                status=0  # Not started
            )
            db.session.add(student_task)
            
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Successfully enrolled in the curriculum!')
        return redirect(url_for('dashboard.index'))
        
    return render_template('curriculum/enroll.html', form=form, curriculum=curriculum)
