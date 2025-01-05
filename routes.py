from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm
from datetime import datetime, timedelta
import pytz
from utils.timezone import now_in_utc, to_user_timezone, from_user_timezone
import logging

logger = logging.getLogger(__name__)

# Blueprint registration
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm
from datetime import datetime, timedelta
import pytz
from utils.timezone import now_in_utc, to_user_timezone, from_user_timezone
import logging

logger = logging.getLogger(__name__)

# Blueprint registration
auth_bp = Blueprint('auth', __name__)
curriculum_bp = Blueprint('curriculum', __name__)
dashboard_bp = Blueprint('dashboard', __name__)

def register_routes(app):
    @app.route('/')
    def root():
        return redirect(url_for('dashboard.index'))

auth_bp = Blueprint('auth', __name__)
curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
archive_bp = Blueprint('archive', __name__, url_prefix='/archive')

@archive_bp.route('/')
@login_required
def index():
    from datetime import datetime, timedelta
    import pytz
    
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    active_enrollments = [e for e in enrollments if not e.is_completed()]
    finished_enrollments = [e for e in enrollments if e.is_completed()]
    
    from utils.timezone import now_in_utc
    now = now_in_utc()
    time_metrics = {}
    
    for enrollment in enrollments:
        tasks = StudentTask.query.join(Task).filter(
            StudentTask.student_id == current_user.id,
            Task.curriculum_id == enrollment.curriculum_id
        ).all()
        
        weekly_time = sum(t.time_spent_minutes for t in tasks 
                         if t.updated_at and pytz.UTC.localize(t.updated_at) >= now - timedelta(days=7))
        monthly_time = sum(t.time_spent_minutes for t in tasks 
                          if t.updated_at and pytz.UTC.localize(t.updated_at) >= now - timedelta(days=30))
        yearly_time = sum(t.time_spent_minutes for t in tasks 
                         if t.updated_at and pytz.UTC.localize(t.updated_at) >= now - timedelta(days=365))
        
        time_metrics[enrollment.id] = {
            'weekly': weekly_time,
            'monthly': monthly_time,
            'yearly': yearly_time
        }
    
    return render_template('archive/index.html',
                         active_enrollments=active_enrollments,
                         finished_enrollments=finished_enrollments,
                         active_count=len(active_enrollments),
                         finished_count=len(finished_enrollments),
                         time_metrics=time_metrics)

@archive_bp.route('/enrollment/<int:id>')
@login_required
def view_enrollment(id):
    enrollment = Enrollment.query.get_or_404(id)
    if enrollment.student_id != current_user.id:
        abort(403)
    
    if not enrollment.curriculum:
        flash('This enrollment has no associated curriculum', 'error')
        return redirect(url_for('archive.index'))
        
    completed_tasks = StudentTask.query.join(Task).filter(
        StudentTask.student_id == current_user.id,
        Task.curriculum_id == enrollment.curriculum_id,
        StudentTask.status.in_([StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED])
    ).all()
    
    total_tasks = len(enrollment.curriculum.tasks)
    finished_tasks = sum(1 for t in completed_tasks if t.status == StudentTask.STATUS_COMPLETED)
    skipped_tasks = sum(1 for t in completed_tasks if t.status == StudentTask.STATUS_SKIPPED)
    
    stats = {
        'total_tasks': total_tasks,
        'finished_tasks': finished_tasks,
        'finished_percent': (finished_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        'skipped_tasks': skipped_tasks,
        'skipped_percent': (skipped_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        'total_time': sum(t.time_spent_minutes for t in completed_tasks),
        'avg_time': sum(t.time_spent_minutes for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0
    }
    
    return render_template('archive/view.html',
                         enrollment=enrollment,
                         completed_tasks=completed_tasks,
                         stats=stats)

@archive_bp.route('/task/<int:id>/unarchive', methods=['POST'])
@login_required
def unarchive_task(id):
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=id
    ).first_or_404()
    
    student_task.status = StudentTask.STATUS_NOT_STARTED
    student_task.started_at = None
    student_task.finished_at = None
    student_task.skipped_at = None
    student_task.time_spent_minutes = 0
    
    db.session.commit()
    return jsonify({'status': 'success'})

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
    
    # Initialize statistics and tasks dictionaries
    tasks_stats = {}
    filtered_tasks = {}
    
    for enrollment in enrollments:
        # Get total and completed task counts
        total_tasks = Task.query.filter_by(curriculum_id=enrollment.curriculum_id).count()
        completed_tasks = StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_COMPLETED
        ).join(Task).filter(Task.curriculum_id == enrollment.curriculum_id).count()
        
        tasks_stats[enrollment.id] = {
            'total': total_tasks,
            'completed': completed_tasks
        }
        
        # Get next 10 incomplete tasks
        incomplete_tasks = Task.query.outerjoin(
            StudentTask, 
            (Task.id == StudentTask.task_id) & 
            (StudentTask.student_id == current_user.id)
        ).filter(
            Task.curriculum_id == enrollment.curriculum_id,
            (StudentTask.status.is_(None)) |  # No student task record
            (StudentTask.status != StudentTask.STATUS_COMPLETED) &  # Not completed
            (StudentTask.status != StudentTask.STATUS_SKIPPED)  # Not skipped
        ).order_by(Task.position).limit(10).all()
        
        filtered_tasks[enrollment.id] = incomplete_tasks
    
    return render_template('dashboard/index.html',
                         enrollments=enrollments,
                         tasks_stats=tasks_stats,
                         filtered_tasks=filtered_tasks,
                         StudentTask=StudentTask,  # Pass the model to the template
                         STATUS_NOT_STARTED=StudentTask.STATUS_NOT_STARTED,
                         STATUS_IN_PROGRESS=StudentTask.STATUS_IN_PROGRESS,
                         STATUS_COMPLETED=StudentTask.STATUS_COMPLETED,
                         STATUS_SKIPPED=StudentTask.STATUS_SKIPPED,
                         current_user=current_user)

@dashboard_bp.route('/task/<int:id>/start', methods=['POST'])
@login_required
def start_task(id):
    logger = logging.getLogger(__name__)
    logger.info(f"Starting task {id} for user {current_user.id}")
    
    try:
        # Begin transaction
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
            logger.info(f"Created new student task for task {id}")
        
        # Reset any other in-progress tasks
        StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).update({
            "status": StudentTask.STATUS_NOT_STARTED,
            "started_at": None
        })
        
        # Start this task
        student_task.start()
        
        db.session.commit()
        logger.info(f"Successfully started task {id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Task started successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'status': student_task.status,
                'link': task.link
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting task {id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f"Failed to start task: {str(e)}"
        }), 500
        
        logger.info(f"Task {id} started successfully")
        return jsonify({
            'status': 'success',
            'message': 'Task started successfully',
            'task_url': task.link,
            'task_id': task.id
        })
        
    except Exception as e:
        logger.error(f"Error starting task {id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/task/<int:id>/finish', methods=['POST'])
@login_required
def finish_task(id):
    try:
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id
        ).first_or_404()
        
        if student_task.can_finish:
            student_task.finish()
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Task completed successfully'
            })
        return jsonify({
            'status': 'error',
            'message': 'Task cannot be finished'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_bp.route('/task/<int:id>/skip', methods=['POST'])
@login_required
def skip_task(id):
    try:
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id
        ).first_or_404()
        
        if student_task.can_skip:
            student_task.skip()
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Task skipped successfully'
            })
        return jsonify({
            'status': 'error',
            'message': 'Task cannot be skipped'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Curriculum routes
@curriculum_bp.route('/')
@login_required
def list():
    # Show published curriculums and private ones created by the current user
    curriculums = Curriculum.query.filter(
        (Curriculum.published == True) | 
        (Curriculum.creator_id == current_user.id)
    ).all()
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
        if not curriculum.locked:
            curriculum.name = form.name.data
            curriculum.description = form.description.data
            curriculum.link = form.link.data
            curriculum.publisher = form.publisher.data
            curriculum.published = bool(request.form.get('published'))
            if request.form.get('locked'):
                curriculum.locked = True
                curriculum.published_at = datetime.now(pytz.UTC)
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