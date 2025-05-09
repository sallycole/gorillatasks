from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from sqlalchemy import text
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot, GRADE_LEVELS
from forms import LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, EnrollmentForm, UserEditForm
from datetime import datetime, timedelta
import pytz
from utils.timezone import now_in_utc, to_user_timezone, from_user_timezone
import logging

logger = logging.getLogger(__name__)

# Blueprint registration
auth_bp = Blueprint('auth', __name__)
curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')
archive_bp = Blueprint('archive', __name__, url_prefix='/archive')
todo_bp = Blueprint('todo', __name__, url_prefix='/todo')

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
                         if t.finished_at and (t.finished_at.tzinfo is None and pytz.UTC.localize(t.finished_at) or t.finished_at) >= now - timedelta(days=7))
        monthly_time = sum(t.time_spent_minutes for t in tasks 
                          if t.finished_at and (t.finished_at.tzinfo is None and pytz.UTC.localize(t.finished_at) or t.finished_at) >= now - timedelta(days=30))
        yearly_time = sum(t.time_spent_minutes for t in tasks 
                         if t.finished_at and (t.finished_at.tzinfo is None and pytz.UTC.localize(t.finished_at) or t.finished_at) >= now - timedelta(days=365))

        # Calculate today's time
        today_time = sum(t.time_spent_minutes for t in tasks 
                        if t.finished_at and (t.finished_at.tzinfo is None and pytz.UTC.localize(t.finished_at) or t.finished_at).date() == now.date())

        # Calculate all time
        all_time = sum(t.time_spent_minutes for t in tasks if t.time_spent_minutes)

        time_metrics[enrollment.id] = {
            'today': today_time,
            'weekly': weekly_time,
            'monthly': monthly_time,
            'yearly': yearly_time,
            'all_time': all_time
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

    total_tasks = enrollment.curriculum.tasks.count()
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
    try:
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id
        ).first_or_404()

        student_task.status = StudentTask.STATUS_NOT_STARTED
        student_task.started_at = None
        student_task.finished_at = None
        student_task.skipped_at = None
        student_task.time_spent_minutes = 0
        student_task.promoted = False

        db.session.commit()

        # If it's an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'success'})

        # Otherwise, redirect back to the enrollment view
        flash('Task successfully unarchived!', 'success')
        return redirect(url_for('archive.view_enrollment', id=request.args.get('enrollment_id')))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unarchiving task: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': str(e)})
        flash(f'Error unarchiving task: {str(e)}', 'danger')
        return redirect(url_for('archive.index'))

@todo_bp.route('/')
@login_required
def index():
    # Get all promoted tasks, including completed adaptive tasks
    promoted_tasks = (StudentTask.query
        .join(Task)
        .filter(
            StudentTask.student_id == current_user.id,
            StudentTask.promoted == True
        )
        .order_by(Task.position)
        .all())

    # Log debugging information
    logger.info(f"User {current_user.id} ({current_user.email}) has {len(promoted_tasks)} promoted tasks")

    # Count tasks by status
    status_counts = {
        "not_started": 0,
        "in_progress": 0,
        "completed": 0,
        "skipped": 0
    }

    # Calculate total time spent on completed tasks
    total_time_spent = 0

    for task in promoted_tasks:
        if task.status == StudentTask.STATUS_NOT_STARTED:
            status_counts["not_started"] += 1
        elif task.status == StudentTask.STATUS_IN_PROGRESS:
            status_counts["in_progress"] += 1
        elif task.status == StudentTask.STATUS_COMPLETED:
            status_counts["completed"] += 1
            total_time_spent += task.time_spent_minutes
        elif task.status == StudentTask.STATUS_SKIPPED:
            status_counts["skipped"] += 1

    logger.info(f"Task status counts: {status_counts}")
    logger.info(f"Total time spent: {total_time_spent} minutes")

    # Group tasks by curriculum
    tasks_by_curriculum = {}
    curriculum_names = {}

    for student_task in promoted_tasks:
        curriculum_id = student_task.task.curriculum_id
        if curriculum_id not in tasks_by_curriculum:
            tasks_by_curriculum[curriculum_id] = []
            # Get curriculum name
            curriculum = Curriculum.query.get(curriculum_id)
            curriculum_names[curriculum_id] = curriculum.name if curriculum else "Unknown Curriculum"
            logger.info(f"Adding curriculum {curriculum_id}: {curriculum_names[curriculum_id]}")

        tasks_by_curriculum[curriculum_id].append(student_task)

    # Log curriculum counts
    for curriculum_id, tasks in tasks_by_curriculum.items():
        logger.info(f"Curriculum {curriculum_id} has {len(tasks)} tasks")

    # Calculate total and completed tasks for the goal display
    total_tasks = len(promoted_tasks)
    completed_tasks = status_counts["completed"]

    # Calculate average time per task
    avg_time_per_task = 0
    if completed_tasks > 0:
        avg_time_per_task = total_time_spent / completed_tasks

    # Convert total time to hours and minutes
    hours_spent = total_time_spent // 60
    minutes_spent = total_time_spent % 60

    logger.info(f"Today's goal stats: {completed_tasks} completed out of {total_tasks} total tasks")
    logger.info(f"Time spent: {hours_spent}h {minutes_spent}m, average: {avg_time_per_task:.1f}m per task")

    # Check if user is phobezcole@gmail.com
    if current_user.email == "phobezcole@gmail.com":
        logger.info("Found user phobezcole@gmail.com - debugging task count")
        # Direct check for all promoted tasks for this user
        all_promoted = StudentTask.query.filter_by(
            student_id=current_user.id,
            promoted=True
        ).all()
        logger.info(f"Direct query shows {len(all_promoted)} promoted tasks")

        # Check database for any inconsistencies
        if len(all_promoted) != len(promoted_tasks):
            logger.warning(f"Discrepancy in task counts: direct {len(all_promoted)} vs joined {len(promoted_tasks)}")

    return render_template('todo/index.html',
                          tasks_by_curriculum=tasks_by_curriculum,
                          curriculum_names=curriculum_names,
                          STATUS_NOT_STARTED=StudentTask.STATUS_NOT_STARTED,
                          STATUS_IN_PROGRESS=StudentTask.STATUS_IN_PROGRESS,
                          STATUS_COMPLETED=StudentTask.STATUS_COMPLETED,
                          STATUS_SKIPPED=StudentTask.STATUS_SKIPPED,
                          completed_tasks=completed_tasks,
                          total_tasks=total_tasks,
                          total_time_spent=total_time_spent,
                          hours_spent=hours_spent,
                          minutes_spent=minutes_spent,
                          avg_time_per_task=avg_time_per_task,
                          current_user=current_user)

@todo_bp.route('/reset', methods=['POST'])
@login_required
def reset_today():
    """
    Manually reset all tasks in the Today list.
    All tasks return to inventory - both completed and unfinished.
    """
    try:
        # Get all promoted tasks
        promoted_tasks = StudentTask.query.filter_by(
            student_id=current_user.id,
            promoted=True
        ).all()

        reset_count = 0
        for task in promoted_tasks:
            # Reset promoted flag for all tasks, regardless of status
            task.promoted = False

            # Only reset status for unfinished tasks
            if task.status in [StudentTask.STATUS_NOT_STARTED, StudentTask.STATUS_IN_PROGRESS]:
                task.status = StudentTask.STATUS_NOT_STARTED
                task.started_at = None

            reset_count += 1

        db.session.commit()

        logger.info(f"User {current_user.id} manually reset {reset_count} tasks (including completed tasks)")

        return jsonify({
            'status': 'success',
            'count': reset_count,
            'message': f'Reset {reset_count} unfinished tasks'
        })
    except Exception as e:
        logger.error(f"Error resetting tasks: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@todo_bp.route('/task/<int:id>/start', methods=['POST'])
@login_required
def start_task(id):
    logger.info(f"Starting task {id} for user {current_user.id} on Today page")
    try:
        # Reset any other in-progress tasks
        StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).update({
            "status": StudentTask.STATUS_NOT_STARTED,
            "started_at": None
        })

        # Get the task to start
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id,
            promoted=True
        ).first_or_404()

        # Start the task
        student_task.start()
        db.session.commit()

        logger.info(f"Task {id} started successfully, status: {student_task.status}")

        return jsonify({
            'status': 'success',
            'message': 'Task started successfully',
            'task': {
                'id': id,
                'status': student_task.status,
                'link': student_task.task.link
            }
        })
    except Exception as e:
        logger.error(f"Error starting task {id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@todo_bp.route('/task/<int:id>/finish', methods=['POST'])
@login_required
def finish_task(id):
    import time
    start_time = time.time()
    logger.info(f"Starting finish_task for task {id}")

    try:
        # Find the student task
        query_start = time.time()
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id,
            promoted=True
        ).first_or_404()
        query_time = time.time() - query_start
        logger.info(f"Task query took {query_time:.3f} seconds")
        logger.info(f"Task {id} finish requested at {datetime.now(pytz.UTC)}")

        # Ensure task can be finished
        if student_task.status != StudentTask.STATUS_IN_PROGRESS:
            logger.warning(f"Attempting to finish task {id} that isn't in progress. Current status: {student_task.status}")
            # If task is already completed, just return success
            if student_task.status == StudentTask.STATUS_COMPLETED:
                return jsonify({
                    'status': 'success',
                    'message': 'Task was already completed',
                    'time_spent': student_task.time_spent_minutes,
                    'task_id': id
                })

        # Finish the task properly
        student_task.status = StudentTask.STATUS_COMPLETED
        student_task.finished_at = datetime.now(pytz.UTC)
        logger.info(f"Set task {id} status to COMPLETED and finished_at to {student_task.finished_at}")

        # Calculate time spent if task was started
        time_spent_minutes = 0
        if student_task.started_at:
            # Ensure started_at is in UTC
            started_at_utc = pytz.UTC.localize(student_task.started_at) if student_task.started_at.tzinfo is None else student_task.started_at.astimezone(pytz.UTC)
            delta = student_task.finished_at - started_at_utc
            student_task.time_spent_minutes = int(delta.total_seconds() / 60)
            time_spent_minutes = student_task.time_spent_minutes
            logger.info(f"Task {id} time spent: {student_task.time_spent_minutes} minutes (started at: {started_at_utc})")
        else:
            logger.warning(f"Task {id} finished but has no start timestamp")

        # Keep promoted flag TRUE so it stays in Today's list for tracking
        commit_start = time.time()
        db.session.commit()
        commit_time = time.time() - commit_start
        logger.info(f"Database commit took {commit_time:.3f} seconds")

        total_time = time.time() - start_time
        logger.info(f"Total finish_task processing time: {total_time:.3f} seconds")

        # Return success response with time spent data
        return jsonify({
            'status': 'success',
            'message': 'Task completed successfully',
            'time_spent': time_spent_minutes,
            'task_id': id
        })
    except Exception as e:
        logger.error(f"Error finishing task {id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f"Task cannot be finished: {str(e)}"
        }), 400

from utils.db_helpers import with_db_retry

@auth_bp.route('/login', methods=['GET', 'POST'])
@with_db_retry
def login():
    if current_user.is_authenticated:
        return redirect(url_for('root'))

    form = LoginForm()
    if form.validate_on_submit():
        # Try finding user by email first, then username
        user = User.query.filter(
            db.or_(
                User.email == form.username.data,
                db.and_(
                    User.username.isnot(None),
                    User.username == form.username.data
                )
            )
        ).first()

        if not user:
            flash('User not found. Please check your email or username.')
            return render_template('auth/login.html', form=form)

        logger.info(f"Login attempt for user {user.email}")

        # Check if password is valid using either method
        is_valid = False
        
        # Try encrypted_password first
        if hasattr(user, 'encrypted_password') and user.encrypted_password:
            if form.password.data == user.encrypted_password:
                logger.info(f"Direct encrypted_password match for user {user.id}")
                is_valid = True
                # Update to new hash format for future
                user.set_password(form.password.data)

        # Try password_hash if not already validated
        if not is_valid and user.password_hash:
            try:
                if check_password_hash(user.password_hash, form.password.data):
                    logger.info(f"Password hash match for user {user.id}")
                    is_valid = True
            except Exception as e:
                logger.error(f"Error checking password hash: {str(e)}")

        if is_valid:
            login_user(user)
            
            # Handle redirect logic
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Log referrer info for debugging
            referrer = request.referrer or ''
            logger.info(f"Login referrer: {referrer}")
            logger.info(f"Login URL: {request.url}")
            
            # Check if came from homepage through login page
            if referrer and '/login' in referrer:
                original_page = request.args.get('next', '')
                logger.info(f"Next parameter: {original_page}")
                if original_page == '/' or original_page == url_for('root'):
                    logger.info("Redirecting back to homepage")
                    return redirect(url_for('root'))
            # Direct login from homepage
            elif referrer and referrer.endswith('/') and '/login' not in referrer:
                logger.info("Direct homepage login, redirecting back to homepage")
                return redirect(url_for('root'))
            
            # Default redirect
            return redirect(url_for('todo.index'))

        flash('Invalid password. Please try again.')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('inventory.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            time_zone=form.time_zone.data
        )
        user.set_password(form.password.data)  # This will set both password_hash and encrypted_password
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('inventory.index'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
@with_db_retry
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

@auth_bp.route('/enrollment/<int:enrollment_id>/toggle_pause', methods=['POST'])
@login_required
def toggle_pause(enrollment_id):
    enrollment = Enrollment.query.filter_by(id=enrollment_id, student_id=current_user.id).first_or_404()
    enrollment.paused = not enrollment.paused
    db.session.commit()
    flash('Enrollment has been ' + ('paused' if enrollment.paused else 'unpaused'))
    return redirect(url_for('auth.account'))

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

# Inventory routes
@inventory_bp.route('/')
@login_required
def index():
    from datetime import datetime
    start_time = datetime.now()

    # Get enrollments and related data in a single optimized query
    enrollments = (Enrollment.query
        .options(db.joinedload(Enrollment.curriculum))
        .filter(
            Enrollment.student_id == current_user.id,
            Enrollment.paused == False
        )
        .all())

    # Early return for no enrollments
    if not enrollments:
        return render_template('inventory/index.html',
                         enrollments=[],
                         tasks_stats={},
                         filtered_tasks={},
                         StudentTask=StudentTask,
                         STATUS_NOT_STARTED=StudentTask.STATUS_NOT_STARTED,
                         STATUS_IN_PROGRESS=StudentTask.STATUS_IN_PROGRESS,
                         STATUS_COMPLETED=StudentTask.STATUS_COMPLETED,
                         STATUS_SKIPPED=StudentTask.STATUS_SKIPPED,
                         current_user=current_user)

    # Get curriculum IDs
    curriculum_ids = [e.curriculum_id for e in enrollments]

    # Single optimized query for task stats
    task_stats = (
        db.session.query(
            Task.curriculum_id,
            Curriculum.is_adaptive,
            db.func.count(Task.id).label('total_tasks'),
            db.func.count(db.case((StudentTask.status == StudentTask.STATUS_COMPLETED, 1))).label('completed_tasks'),
            db.func.count(db.case((StudentTask.status == StudentTask.STATUS_SKIPPED, 1))).label('skipped_tasks')
        )
        .join(Curriculum, Task.curriculum_id == Curriculum.id)
        .outerjoin(StudentTask, db.and_(
            StudentTask.task_id == Task.id,
            StudentTask.student_id == current_user.id
        ))
        .filter(Task.curriculum_id.in_(curriculum_ids))
        .group_by(Task.curriculum_id, Curriculum.is_adaptive)
    )

    # Early return for no enrollments
    if not enrollments:
        return render_template('inventory/index.html',
                         enrollments=[],
                         tasks_stats={},
                         filtered_tasks={},
                         StudentTask=StudentTask,
                         STATUS_NOT_STARTED=StudentTask.STATUS_NOT_STARTED,
                         STATUS_IN_PROGRESS=StudentTask.STATUS_IN_PROGRESS,
                         STATUS_COMPLETED=StudentTask.STATUS_COMPLETED,
                         STATUS_SKIPPED=StudentTask.STATUS_SKIPPED,
                         current_user=current_user)

    # Get all curriculum IDs
    curriculum_ids = [e.curriculum_id for e in enrollments]

    # Bulk fetch all student tasks for these curriculums
    student_tasks = (StudentTask.query
        .join(Task)
        .filter(
            StudentTask.student_id == current_user.id,
            Task.curriculum_id.in_(curriculum_ids)
        )
        .all())

    # Create lookup dictionary for student tasks
    student_task_map = {}
    for st in student_tasks:
        if st.task_id not in student_task_map:
            student_task_map[st.task_id] = st

    # Restructure stats with curriculum_id as key
    curriculum_stats = {}
    for r in task_stats:
        curr_id, is_adaptive = r[0], r[1]
        curriculum_stats[curr_id] = {
            'total': r[2], 
            'completed': r[3] or 0,  # Handle None values 
            'skipped': r[4] or 0,
            'is_adaptive': is_adaptive
        }

    # Prepare tasks stats and filtered tasks
    tasks_stats = {}
    filtered_tasks = {}

    # Get all tasks and student tasks in two efficient bulk queries
    all_tasks = {}
    all_student_tasks = {}

    # Query all tasks for these curriculums, with ordering
    tasks_query = Task.query.filter(Task.curriculum_id.in_(curriculum_ids)).order_by(Task.position).all()

    # Group tasks by curriculum_id
    for task in tasks_query:
        if task.curriculum_id not in all_tasks:
            all_tasks[task.curriculum_id] = []
        all_tasks[task.curriculum_id].append(task)

    # Get all student tasks for this user in one query
    student_tasks_query = (StudentTask.query
        .join(Task)
        .filter(
            StudentTask.student_id == current_user.id,
            Task.curriculum_id.in_(curriculum_ids)
        )
        .all())

    # Group student tasks by task_id
    for st in student_tasks_query:
        all_student_tasks[st.task_id] = st

    # Process enrollments more efficiently using preloaded data
    for enrollment in enrollments:
        curr_id = enrollment.curriculum_id
        tasks_stats[enrollment.id] = curriculum_stats.get(curr_id, {'total': 0, 'completed': 0, 'skipped': 0, 'is_adaptive': False})

        curriculum = enrollment.curriculum
        if curriculum.is_adaptive:
            # For adaptive curriculums, use preloaded tasks
            filtered_tasks[enrollment.id] = all_tasks.get(curr_id, [])[:10]
        else:
            # For regular curriculums, filter incomplete tasks from preloaded data
            tasks_for_curr = all_tasks.get(curr_id, [])
            incomplete_tasks = []
            for task in tasks_for_curr:
                student_task = all_student_tasks.get(task.id)
                if not student_task or student_task.status not in [StudentTask.STATUS_COMPLETED, StudentTask.STATUS_SKIPPED]:
                    incomplete_tasks.append(task)
                    if len(incomplete_tasks) >= 10:
                        break
            filtered_tasks[enrollment.id] = incomplete_tasks

    # Log the time taken
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    logger.info(f"Inventory page prepared in {elapsed:.2f} seconds for user {current_user.id}")

    return render_template('inventory/index.html',
                         enrollments=enrollments,
                         tasks_stats=tasks_stats,
                         filtered_tasks=filtered_tasks,
                         StudentTask=StudentTask,
                         STATUS_NOT_STARTED=StudentTask.STATUS_NOT_STARTED,
                         STATUS_IN_PROGRESS=StudentTask.STATUS_IN_PROGRESS,
                         STATUS_COMPLETED=StudentTask.STATUS_COMPLETED,
                         STATUS_SKIPPED=StudentTask.STATUS_SKIPPED,
                         current_user=current_user)

@inventory_bp.route('/task/<int:id>/start', methods=['POST'])
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

@inventory_bp.route('/task/<int:id>/finish', methods=['POST'])
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

@inventory_bp.route('/task/<int:id>/skip', methods=['POST'])
@login_required
def skip_task(id):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Skip task request received for task {id} from user {current_user.id} (attempt {retry_count + 1})")
            
            # Verify task exists
            task = Task.query.get(id)
            if not task:
                logger.error(f"Task {id} not found")
                return jsonify({
                    'status': 'error',
                    'message': 'Task not found'
                }), 404

            # Get or create student task with retry logic
            for _ in range(3):
                try:
                    student_task = StudentTask.query.filter_by(
                        student_id=current_user.id,
                        task_id=id
                    ).with_for_update().first()
                    
                    if not student_task:
                        student_task = StudentTask(
                            student_id=current_user.id,
                            task_id=id,
                            status=StudentTask.STATUS_NOT_STARTED
                        )
                        db.session.add(student_task)
                    break
                except Exception as e:
                    logger.warning(f"Retrying student task query: {str(e)}")
                    db.session.rollback()
                    continue

            # Skip the task if not already completed
            if student_task.status == StudentTask.STATUS_COMPLETED:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot skip completed task'
                }), 400

            student_task.skip()
            db.session.commit()
            logger.info(f"Task {id} skipped successfully")
            
            return jsonify({
                'status': 'success',
                'message': 'Task skipped successfully',
                'task': {
                    'id': id,
                    'status': student_task.status
                }
            })

        except Exception as e:
            db.session.rollback()
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Final error skipping task {id} after {max_retries} attempts: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to skip task after {max_retries} attempts: {str(e)}"
                }), 500
            else:
                logger.warning(f"Retrying skip operation for task {id} after error: {str(e)}")
                import time
                time.sleep(1)  # Wait 1 second before retrying

@inventory_bp.route('/task/<int:id>/promote', methods=['POST'])
@login_required
def promote_task(id):
    logger.info(f"Promoting task {id} for user {current_user.id}")
    try:
        # First check if the task exists
        task = Task.query.get(id)
        if not task:
            logger.error(f"Task {id} not found")
            response = jsonify({
                'status': 'error',
                'message': f'Task with ID {id} not found'
            })
            response.status_code = 404
            response.headers['Content-Type'] = 'application/json'
            return response

        # Now get or create the student task
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=id
        ).first()

        # For adaptive tasks, we need special handling
        if task.is_adaptive:
            # For adaptive tasks, we always create a new task instance if
            # there isn't an active one or the existing one is completed
            if not student_task or student_task.status == StudentTask.STATUS_COMPLETED:
                logger.info(f"Creating new student task for adaptive task {id}")
                student_task = StudentTask(
                    student_id=current_user.id,
                    task_id=id,
                    status=StudentTask.STATUS_NOT_STARTED
                )
                db.session.add(student_task)
        elif not student_task:
            # For regular tasks, create a new task entry if none exists
            logger.info(f"Creating new student task for task {id}")
            student_task = StudentTask(
                student_id=current_user.id,
                task_id=id,
                status=StudentTask.STATUS_NOT_STARTED
            )
            db.session.add(student_task)

        logger.info(f"Current status of task {id}: {student_task.status}")

        if student_task.status in [StudentTask.STATUS_NOT_STARTED, StudentTask.STATUS_IN_PROGRESS]:
            logger.info(f"Promoting task {id} to today")
            student_task.promoted = True
            db.session.commit()
            logger.info(f"Task {id} promoted successfully")

            # Make sure we return proper JSON response
            response = jsonify({
                'status': 'success',
                'message': 'Task promoted to today successfully'
            })
            response.headers['Content-Type'] = 'application/json'
            return response

        logger.warning(f"Task {id} cannot be promoted due to status: {student_task.status}")

        # Make sure we set Content-Type header explicitly
        response = jsonify({
            'status': 'error',
            'message': 'Only tasks that are not started or in progress can be promoted'
        })
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        logger.error(f"Error promoting task {id}: {str(e)}", exc_info=True)
        db.session.rollback()

        # Explicitly set Content-Type to application/json
        response = jsonify({
            'status': 'error',
            'message': f"Failed to promote task: {str(e)}"
        })
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        return response

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
        form_type = request.form.get('form_type', 'manual')

        logger.info(f"Processing curriculum form with type: {form_type}")

        if form_type == 'xml' and form.xml_file.data:
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
                    grade_levels=[grade.text.strip() for grade in root.findall('grade_levels/grade_level')] if root.find('grade_levels') is not None else [],
                    is_adaptive=False
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
                logger.error(f"Error processing XML file: {str(e)}")
                flash(f'Error processing XML file: {str(e)}', 'error')
                return render_template('curriculum/edit.html', form=form, grade_levels=GRADE_LEVELS)
        elif form_type == 'adaptive':
            # Handle adaptive curriculum creation
            try:
                logger.info(f"Creating adaptive curriculum: {form.name.data}")
                logger.info(f"Grade levels: {request.form.getlist('grade_levels')}")

                curriculum = Curriculum(
                    name=form.name.data,
                    description=form.description.data,
                    link=form.link.data,
                    public=False,  # All new curriculums start as private
                    creator_id=current_user.id,
                    publisher=form.publisher.data,
                    grade_levels=request.form.getlist('grade_levels'),
                    is_adaptive=True
                )
                db.session.add(curriculum)
                db.session.flush()  # Get curriculum.id without committing

                # Create the single adaptive task
                task = Task(
                    curriculum_id=curriculum.id,
                    title=request.form.get('adaptive_task_title', 'Practice Session'),
                    description=request.form.get('adaptive_task_description', 'Complete one session'),
                    link=form.link.data,  # Use same link as curriculum
                    action=Task.ACTION_MAP.get(request.form.get('adaptive_task_action', 'Do'), Task.ACTION_DO),
                    position=1,
                    is_adaptive=True
                )
                db.session.add(task)
                db.session.commit()
                logger.info(f"Adaptive curriculum created successfully with ID: {curriculum.id}")

                flash('Adaptive curriculum created successfully. You can now enroll in it from the curriculums page.')
                return redirect(url_for('curriculum.list'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating adaptive curriculum: {str(e)}")
                flash(f'Error creating adaptive curriculum: {str(e)}', 'error')
                return render_template('curriculum/edit.html', form=form, grade_levels=GRADE_LEVELS, form_type='adaptive')
        else:
            # Handle manual curriculum creation
            curriculum = Curriculum(
                name=form.name.data,
                description=form.description.data,
                link=form.link.data,
                public=False,  # All new curriculums start as private
                creator_id=current_user.id,
                publisher=form.publisher.data,
                grade_levels=request.form.getlist('grade_levels'),
                is_adaptive=False
            )
            db.session.add(curriculum)
            db.session.commit()
            flash('Curriculum created successfully!')
            return redirect(url_for('curriculum.list'))
    return render_template('curriculum/edit.html', form=form, grade_levels=GRADE_LEVELS)

@curriculum_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    curriculum = Curriculum.query.get_or_404(id)
    return render_template('curriculum/view.html', curriculum=curriculum)

@curriculum_bp.route('/<int:id>/publish', methods=['POST'])
@login_required
def publish(id):
    curriculum = Curriculum.query.get_or_404(id)
    if not current_user.is_superuser:
        flash('Only superusers can publish curriculums')
        return redirect(url_for('curriculum.view', id=id))
    if curriculum.creator_id != current_user.id and not current_user.is_superuser:
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

    if curriculum.enrollments.count() > 0:
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
        # Get the highest current position and add 1
        max_position = db.session.query(db.func.max(Task.position)).filter(Task.curriculum_id == curriculum.id).scalar() or 0
        position = max_position + 1
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
        return redirect(url_for('inventory.index'))

    return render_template('curriculum/enroll.html', form=form, curriculum=curriculum)

def init_routes(app):
    # Initialize additional routes if needed
    pass