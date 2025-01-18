from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm, UserEditForm
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
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm, UserEditForm
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

@auth_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UserEditForm(obj=current_user)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.time_zone = form.time_zone.data
        db.session.commit()
        flash('Your information has been updated.')
        return redirect(url_for('auth.account'))
        
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).join(Curriculum).all()
    return render_template('auth/account.html', enrollments=enrollments, form=form)

@auth_bp.route('/unenroll/<int:enrollment_id>', methods=['POST'])
@login_required
def unenroll(enrollment_id):
    enrollment = Enrollment.query.filter_by(id=enrollment_id, student_id=current_user.id).first_or_404()
    db.session.delete(enrollment)
    db.session.commit()
    flash('Successfully unenrolled from the curriculum.')
    return redirect(url_for('auth.account'))

@auth_bp.route('/enrollment/<int:enrollment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_enrollment(enrollment_id):
    enrollment = Enrollment.query.filter_by(id=enrollment_id, student_id=current_user.id).first_or_404()
    form = EnrollmentForm(obj=enrollment)
    
    if form.validate_on_submit():
        enrollment.study_days_per_week = form.study_days_per_week.data
        enrollment.target_completion_date = form.target_completion_date.data
        enrollment.weekly_goal_count = enrollment.calculate_weekly_goal()
        db.session.commit()
        flash('Enrollment settings updated successfully.')
        return redirect(url_for('auth.account'))
        
    return render_template('auth/edit_enrollment.html', form=form, enrollment=enrollment)

# Dashboard routes
@dashboard_bp.route('/')
@login_required
def index():
    # Get enrollments with related data
    enrollments = (Enrollment.query
        .options(
            db.joinedload(Enrollment.curriculum)
            .joinedload(Curriculum.tasks)
            .joinedload(Task.student_tasks)
        )
        .filter_by(student_id=current_user.id)
        .all())

    # Recalculate weekly goals with forced commit
    for enrollment in enrollments:
        enrollment.weekly_goal_count = enrollment.calculate_weekly_goal()
        db.session.add(enrollment)
    db.session.commit()
    db.session.expire_all()

    # Get all task stats in a single query
    task_stats_query = (db.session.query(
            Task.curriculum_id,
            db.func.count(Task.id).label('total_tasks'),
            db.func.count(db.case(
                (StudentTask.status == StudentTask.STATUS_COMPLETED, 1),
                else_=None
            )).label('completed_tasks')
        )
        .outerjoin(StudentTask, db.and_(
            Task.id == StudentTask.task_id,
            StudentTask.student_id == current_user.id
        ))
        .group_by(Task.curriculum_id)
        .all())

    # Process stats
    tasks_stats = {}
    filtered_tasks = {}
    curriculum_stats = {r[0]: {'total': r[1], 'completed': r[2]} for r in task_stats_query}

    for enrollment in enrollments:
        curr_id = enrollment.curriculum_id
        tasks_stats[enrollment.id] = curriculum_stats.get(curr_id, {'total': 0, 'completed': 0})

        # Filter incomplete tasks in memory since we already loaded them
        incomplete_tasks = [
            task for task in enrollment.curriculum.tasks
            if not any(st.status in [StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED] 
                      for st in task.student_tasks if st.student_id == current_user.id)
        ][:10]  # Limit to 10 tasks
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
    # Show user's own curriculums and any published ones
    curriculums = Curriculum.query.filter(
        db.or_(
            Curriculum.creator_id == current_user.id,
            Curriculum.published == True
        )
    ).all()
    logger.info(f"Found {len(curriculums)} curriculums for user {current_user.email}")
    for c in curriculums:
        logger.info(f"Curriculum: {c.id} - {c.name} - Creator: {c.creator_id}")
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
                # Escape ampersands in URLs but preserve existing escaped ampersands
                xml_content = xml_content.replace("&amp;", "TEMP_AMP")\
                                       .replace("&", "&amp;")\
                                       .replace("TEMP_AMP", "&amp;")
                root = ET.fromstring(xml_content)
                
                # Extract curriculum data from XML
                curriculum = Curriculum(
                    name=root.find('name').text.strip(),
                    description=root.find('description').text.strip(),
                    link=root.find('link').text.strip() if root.find('link') is not None else None,
                    public=False,  # All new curriculums start as private
                    creator_id=current_user.id,
                    publisher=root.find('publisher').text.strip() if root.find('publisher') is not None else None,
                    grade_levels=[grade.text.strip() for grade in root.findall('grade_levels/grade_level')] if root.find('grade_levels') is not None else []
                )
                db.session.add(curriculum)
                db.session.flush()  # Get curriculum.id without committing
                
                # Process tasks
                tasks_element = root.find('tasks')
                if tasks_element is not None:
                    position = 1
                    for task_elem in tasks_element.findall('task'):
                        action_elem = task_elem.find('action')
                        action_text = action_elem.text.strip() if action_elem is not None and action_elem.text else 'Read'
                        action_value = Task.ACTION_MAP.get(action_text, Task.ACTION_READ)
                        
                        task = Task(
                            curriculum_id=curriculum.id,
                            title=task_elem.find('title').text.strip() if task_elem.find('title') is not None and task_elem.find('title').text else '',
                            description=task_elem.find('description').text.strip() if task_elem.find('description') is not None and task_elem.find('description').text else '',
                            link=task_elem.find('url').text.strip() if task_elem.find('url') is not None and task_elem.find('url').text else None,
                            action=action_value,
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

@curriculum_bp.route('/<int:id>/publish', methods=['POST'])
@login_required
def publish(id):
    curriculum = Curriculum.query.get_or_404(id)
    if curriculum.creator_id != current_user.id:
        flash('You can only publish your own curriculums')
        return redirect(url_for('curriculum.view', id=id))
    
    curriculum.published = True
    curriculum.locked = True
    curriculum.published_at = datetime.now(pytz.UTC)
    db.session.commit()
    flash('Curriculum published successfully!')
    return redirect(url_for('curriculum.view', id=id))

@curriculum_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    curriculum = Curriculum.query.get_or_404(id)
    if curriculum.creator_id != current_user.id:
        flash('You can only delete your own curriculums')
        return redirect(url_for('curriculum.list'))
    
    if curriculum.enrollments:
        flash('Cannot delete curriculum with active enrollments')
        return redirect(url_for('curriculum.view', id=curriculum.id))
    
    try:
        # Delete associated student_tasks first
        task_ids = [task.id for task in curriculum.tasks]
        StudentTask.query.filter(StudentTask.task_id.in_(task_ids)).delete(synchronize_session=False)
        # Then delete tasks
        Task.query.filter_by(curriculum_id=curriculum.id).delete()
        # Then delete the curriculum
        db.session.delete(curriculum)
        db.session.commit()
        flash('Curriculum deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting curriculum: ' + str(e))
        
    return redirect(url_for('curriculum.list'))

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
            curriculum.grade_levels = request.form.getlist('grade_levels')
            curriculum.published = bool(request.form.get('published'))
            if request.form.get('locked'):
                curriculum.locked = True
                curriculum.published_at = datetime.now(pytz.UTC)
            db.session.commit()
        flash('Curriculum updated successfully!')
        return redirect(url_for('curriculum.view', id=curriculum.id))
    return render_template('curriculum/edit.html', form=form, curriculum=curriculum)

@curriculum_bp.route('/<int:id>/tasks/add', methods=['POST'])
@login_required
def add_task(id):
    curriculum = Curriculum.query.get_or_404(id)
    if curriculum.creator_id != current_user.id:
        flash('You can only edit your own curriculums')
        return redirect(url_for('curriculum.list'))
    
    if not curriculum.locked:
        position = len(curriculum.tasks) + 1
        task = Task(
            curriculum_id=curriculum.id,
            title=request.form['title'],
            description=request.form['description'],
            action=Task.ACTION_MAP[request.form['action']],
            link=request.form['url'] if request.form['url'] else None,
            position=position
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!')
    return redirect(url_for('curriculum.view', id=curriculum.id))

@curriculum_bp.route('/<int:curriculum_id>/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(curriculum_id, task_id):
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    if curriculum.creator_id != current_user.id:
        flash('You can only edit your own curriculums')
        return redirect(url_for('curriculum.list'))
    
    if not curriculum.locked:
        task = Task.query.get_or_404(task_id)
        task.title = request.form['title']
        task.description = request.form['description']
        task.action = Task.ACTION_MAP[request.form['action']]
        task.link = request.form['url'] if request.form['url'] else None
        db.session.commit()
        flash('Task updated successfully!')
    return redirect(url_for('curriculum.view', id=curriculum.id))

@curriculum_bp.route('/<int:curriculum_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(curriculum_id, task_id):
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    if curriculum.creator_id != current_user.id:
        flash('You can only edit your own curriculums')
        return redirect(url_for('curriculum.list'))
    
    if not curriculum.locked:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully!')
    return redirect(url_for('curriculum.edit', id=curriculum_id))

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