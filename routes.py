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
    print(f"Found {len(curriculums)} curriculums")
    for curriculum in curriculums:
        print(f"Curriculum: {curriculum.name}, Creator: {curriculum.creator_id}, Current User: {current_user.id}")
    return render_template('curriculum/list.html', 
                         curriculums=curriculums)

import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import os

@curriculum_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = CurriculumForm()
    if form.validate_on_submit():
        if form.xml_file.data:
            # Process XML file upload first
            try:
                xml_content = form.xml_file.data.read().decode('utf-8')
                root = ET.fromstring(xml_content)
                
                # Extract curriculum data from XML
                curriculum = Curriculum(
                    name=root.find('name').text.strip(),
                    description=root.find('description').text.strip(),
                    link=root.find('link').text.strip() if root.find('link') is not None else None,
                    public=False,  # All new curriculums start as private
                    creator_id=current_user.id,
                    publisher=root.find('publisher').text.strip() if root.find('publisher') is not None else None
                )
                db.session.add(curriculum)
                db.session.flush()  # Get curriculum.id without committing
                
                # Process tasks
                tasks_element = root.find('tasks')
                if tasks_element is not None:
                    position = 1
                    for task_elem in tasks_element.findall('task'):
                        task = Task(
                            curriculum_id=curriculum.id,
                            title=task_elem.find('title').text.strip(),
                            description=task_elem.find('description').text.strip() if task_elem.find('description').text else '',
                            link=task_elem.find('url').text.strip() if task_elem.find('url') is not None else None,
                            position=position
                        )
                        db.session.add(task)
                        position += 1
                
                db.session.commit()
                flash('Curriculum and tasks created successfully from XML!')
                return redirect(url_for('curriculum.list'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing XML file: {str(e)}', 'error')
                return render_template('curriculum/edit.html', form=form)
        else:
            # Handle manual curriculum creation
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

@curriculum_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    curriculum = Curriculum.query.get_or_404(id)
    return render_template('curriculum/view.html', curriculum=curriculum)

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
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        curriculum_id=curriculum.id
    ).first()
    
    if existing_enrollment:
        flash('You are already enrolled in this curriculum.')
        return redirect(url_for('curriculum.view', id=curriculum.id))
    
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
