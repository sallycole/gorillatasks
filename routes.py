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
    # Get user's enrollments
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Initialize statistics dictionary
    tasks_stats = {}
    
    for enrollment in enrollments:
        total_tasks = Task.query.filter_by(curriculum_id=enrollment.curriculum_id).count()
        completed_tasks = StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_COMPLETED
        ).join(Task).filter(Task.curriculum_id == enrollment.curriculum_id).count()
        
        tasks_stats[enrollment.id] = {
            'total': total_tasks,
            'completed': completed_tasks
        }
    
    return render_template('dashboard/index.html',
                         enrollments=enrollments,
                         tasks_stats=tasks_stats,
                         StudentTask=StudentTask)

@dashboard_bp.route('/start_task/<int:id>', methods=['POST'])
@login_required
def start_task(id):
    task = Task.query.get_or_404(id)
    
    # Get or create student task
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=task.id
    ).first()
    
    if not student_task:
        student_task = StudentTask(
            student_id=current_user.id,
            task_id=task.id,
            status=StudentTask.STATUS_NOT_STARTED
        )
        db.session.add(student_task)
    
    if student_task.status == StudentTask.STATUS_NOT_STARTED:
        # Mark all tasks in all curriculums as not started
        student_tasks_in_progress = StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).all()
        
        for st in student_tasks_in_progress:
            st.status = StudentTask.STATUS_NOT_STARTED
            st.started_at = None
        
        # Set this task as active
        student_task.status = StudentTask.STATUS_IN_PROGRESS
        student_task.started_at = datetime.utcnow()
        student_task.finished_at = None
        student_task.skipped_at = None
        student_task.time_spent_minutes = 0
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'task_status': 'in_progress',
            'task_url': task.link if task.link else None
        })
    
    return jsonify({'status': 'error', 'message': 'Task cannot be started'}), 400

@dashboard_bp.route('/finish_task/<int:id>', methods=['POST'])
@login_required
def finish_task(id):
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=id
    ).first_or_404()
    
    if student_task.can_finish:
        student_task.status = StudentTask.STATUS_COMPLETED
        student_task.finished_at = datetime.utcnow()
        if student_task.started_at:
            delta = student_task.finished_at - student_task.started_at
            student_task.time_spent_minutes = int(delta.total_seconds() / 60)
        db.session.commit()
        
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/skip_task/<int:id>', methods=['POST'])
@login_required
def skip_task(id):
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=id
    ).first_or_404()
    
    if student_task.can_skip:
        student_task.status = StudentTask.STATUS_SKIPPED
        student_task.skipped_at = datetime.utcnow()
        student_task.started_at = None
        student_task.finished_at = None
        student_task.time_spent_minutes = 0
        db.session.commit()
        
    return redirect(url_for('dashboard.index'))

# Curriculum routes
@curriculum_bp.route('/')
@login_required
def list():
    curriculums = Curriculum.query.all()
    # Get user's enrollments
    user_enrollments = set(
        enrollment.curriculum_id 
        for enrollment in Enrollment.query.filter_by(student_id=current_user.id).all()
    )
    
    print(f"DEBUG: Found {len(curriculums)} curriculums")
    print(f"DEBUG: User enrollments: {user_enrollments}")
    print(f"DEBUG: Current user id: {current_user.id}")
    
    for curriculum in curriculums:
        print(f"DEBUG: Curriculum {curriculum.id}: {curriculum.name}")
        print(f"DEBUG: - Creator: {curriculum.creator_id}")
        print(f"DEBUG: - Is enrolled: {curriculum.id in user_enrollments}")
        
    return render_template('curriculum/list.html', 
                         curriculums=curriculums,
                         user_enrollments=user_enrollments)

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
            study_days_per_week=form.study_days_per_week.data,
            target_completion_date=form.target_completion_date.data
        )
        db.session.add(enrollment)
        db.session.flush()  # Get the enrollment ID
        
        # Calculate and set the weekly goal
        enrollment.weekly_goal_count = enrollment.calculate_weekly_goal()
        
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