import logging
from flask import request
from flask_login import current_user
from app import socketio, db
from models import Task, StudentTask
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False
    logger.info(f'Client connected: {request.sid}')
    return True

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('start_task')
def handle_start_task(data):
    logger.info(f'Received start_task event: {data}')
    if not current_user.is_authenticated:
        logger.warning('Unauthenticated user attempted to start task')
        return {'status': 'error', 'message': 'Authentication required'}

    try:
        task_id = data.get('task_id')
        if not task_id:
            logger.error('No task_id provided')
            return {'status': 'error', 'message': 'No task ID provided'}

        # Get the task first to ensure it exists
        task = Task.query.get(task_id)
        if not task:
            logger.error(f'Task not found: {task_id}')
            return {'status': 'error', 'message': 'Task not found'}

        # Get or create student task
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()
        
        if not student_task:
            logger.info(f'Creating new student task for task {task_id}')
            student_task = StudentTask(
                student_id=current_user.id,
                task_id=task_id,
                status=StudentTask.STATUS_NOT_STARTED
            )
            db.session.add(student_task)
        
        # Reset any other in-progress tasks
        StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).update({
            "status": StudentTask.STATUS_NOT_STARTED,
            "started_at": None
        })
        
        # Start this task
        student_task.status = StudentTask.STATUS_IN_PROGRESS
        student_task.started_at = datetime.now(pytz.UTC)
        student_task.finished_at = None
        student_task.skipped_at = None
        student_task.time_spent_minutes = 0
        
        db.session.commit()
        logger.info(f'Successfully started task {task_id} for user {current_user.id}')
        
        # Emit task update to all clients
        update_data = {
            'task_id': task_id,
            'status': StudentTask.STATUS_IN_PROGRESS,
            'link': task.link if task.link else None
        }
        socketio.emit('task_updated', update_data, to=request.sid)
        logger.info(f'Emitted task_updated event: {update_data}')
        
        return {'status': 'success', 'message': 'Task started successfully'}
        
    except Exception as e:
        logger.error(f'Error starting task: {str(e)}')
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@socketio.on('finish_task')
def handle_finish_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    try:
        task_id = data.get('task_id')
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first_or_404()
        
        if student_task.can_finish:
            student_task.status = StudentTask.STATUS_COMPLETED
            student_task.finished_at = datetime.now(pytz.UTC)
            if student_task.started_at:
                # Convert naive datetime to UTC if needed
                if student_task.started_at.tzinfo is None:
                    student_task.started_at = pytz.UTC.localize(student_task.started_at)
                delta = student_task.finished_at - student_task.started_at
                student_task.time_spent_minutes = int(delta.total_seconds() / 60)
            
            db.session.commit()

            # Get next 10 incomplete tasks
            next_tasks = Task.query.outerjoin(
                StudentTask,
                (Task.id == StudentTask.task_id) & 
                (StudentTask.student_id == current_user.id)
            ).filter(
                Task.curriculum_id == student_task.task.curriculum_id,
                (StudentTask.status.is_(None)) |  
                ((StudentTask.status != StudentTask.STATUS_COMPLETED) & 
                (StudentTask.status != StudentTask.STATUS_SKIPPED))
            ).order_by(Task.position).limit(10).all()

            # Format tasks for response
            tasks_data = [{
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'link': task.link
            } for task in next_tasks]

            update_data = {
                'task_id': task_id,
                'status': StudentTask.STATUS_COMPLETED,
                'next_tasks': tasks_data
            }
            
            socketio.emit('task_updated', update_data, room=request.sid)
            return {'status': 'success', 'message': 'Task completed successfully'}
            
        return {'status': 'error', 'message': 'Task cannot be finished'}
        
    except Exception as e:
        logger.error(f'Error finishing task: {str(e)}')
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@socketio.on('skip_task')
def handle_skip_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    try:
        task_id = data.get('task_id')
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first_or_404()
        
        if student_task.can_skip:
            student_task.status = StudentTask.STATUS_SKIPPED
            student_task.skipped_at = datetime.now(pytz.UTC)
            student_task.started_at = None
            student_task.finished_at = None
            student_task.time_spent_minutes = 0
            
            db.session.commit()
            
            socketio.emit('task_updated', {
                'task_id': task_id,
                'status': StudentTask.STATUS_SKIPPED
            }, room=request.sid)
            
            return {'status': 'success', 'message': 'Task skipped successfully'}
            
        return {'status': 'error', 'message': 'Task cannot be skipped'}
        
    except Exception as e:
        logger.error(f'Error skipping task: {str(e)}')
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}
