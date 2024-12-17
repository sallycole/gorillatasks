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
    page = request.args.get('page', 1, type=int)
    curriculum_id = request.args.get('curriculum_id', type=int)
    
    # Get user's enrollments
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Initialize statistics dictionaries
    tasks_stats = {}
    task_status = {}
    current_page = {}
    
    for enrollment in enrollments:
        # Get tasks for this enrollment with pagination
        tasks_query = Task.query.filter_by(curriculum_id=enrollment.curriculum_id)
        total_tasks = tasks_query.count()
        
        if curriculum_id == enrollment.id:
            current_page[enrollment.id] = page
            tasks = tasks_query.offset((page - 1) * 10).limit(10).all()
        else:
            current_page[enrollment.id] = 1
            tasks = tasks_query.limit(10).all()
        
        # Calculate statistics
        completed_tasks = StudentTask.query.filter_by(
            student_id=current_user.id,
            status=2  # Completed status
        ).join(Task).filter(Task.curriculum_id == enrollment.curriculum_id).count()
        
        tasks_stats[enrollment.id] = {
            'total': total_tasks,
            'completed': completed_tasks
        }
        
        # Get status for displayed tasks
        for task in tasks:
            student_task = StudentTask.query.filter_by(
                student_id=current_user.id,
                task_id=task.id
            ).first()
            
            if student_task:
                status = 'completed' if student_task.status == 2 else 'in_progress'
            else:
                status = 'not_started'
            
            task_status[(enrollment.id, task.id)] = status
    
    return render_template('dashboard/index.html',
                         enrollments=enrollments,
                         tasks_stats=tasks_stats,
                         task_status=task_status,
                         current_page=current_page)

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
            public=False,  # All new curriculums start as private
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
        # public status is managed separately, not through the edit form
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
