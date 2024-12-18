
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
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    try:
        # Check if user has any in-progress tasks across all curriculums
        in_progress = StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).first()
        
        if in_progress:
            return {'status': 'error', 'message': 'Please finish or skip your in-progress task first'}
            
        task_id = data.get('task_id')
        task = Task.query.get(task_id)
        if not task:
            return {'status': 'error', 'message': 'Task not found'}
            
        # Get or create student task
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()
        
        if not student_task:
            student_task = StudentTask(
                student_id=current_user.id,
                task_id=task_id,
                status=StudentTask.STATUS_NOT_STARTED
            )
            db.session.add(student_task)
            
        # Start the task with UTC timestamp
        now = datetime.now(pytz.UTC)
        student_task.status = StudentTask.STATUS_IN_PROGRESS
        student_task.started_at = now
        student_task.finished_at = None
        student_task.skipped_at = None
        
        # Start this task
        student_task.start()  # Uses the model's start() method
        db.session.commit()
        
        # Send update with task URL to client
        socketio.emit('task_updated', {
            'task_id': task_id,
            'status': StudentTask.STATUS_IN_PROGRESS,
            'link': task.link
        }, room=request.sid)
        
        # Send update to client
        socketio.emit('task_updated', {
            'task_id': task_id,
            'status': StudentTask.STATUS_IN_PROGRESS,
            'link': task.link
        }, room=request.sid)
        
        return {'status': 'success', 'message': 'Task started successfully'}
        
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@socketio.on('finish_task')
def handle_finish_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    try:
        task_id = data.get('task_id')
        task = Task.query.get(task_id)
        if not task:
            return {'status': 'error', 'message': 'Task not found'}
            
        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()

        if not student_task:
            return {'status': 'error', 'message': 'Task not found'}
            
        if student_task.status == StudentTask.STATUS_IN_PROGRESS:
            student_task.status = StudentTask.STATUS_COMPLETED
            student_task.finished_at = datetime.now(pytz.UTC)
            db.session.commit()

            # Get next 10 incomplete tasks
            next_tasks = Task.query.outerjoin(
                StudentTask,
                (Task.id == StudentTask.task_id) & 
                (StudentTask.student_id == current_user.id)
            ).filter(
                Task.curriculum_id == task.curriculum_id,
                (StudentTask.status.is_(None)) |
                (StudentTask.status.in_([StudentTask.STATUS_NOT_STARTED]))
            ).order_by(Task.position).limit(10).all()
            
            # Format tasks for response
            tasks_data = [{
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'link': task.link
            } for task in next_tasks]
            
            socketio.emit('task_updated', {
                'task_id': task_id,
                'status': StudentTask.STATUS_COMPLETED,
                'next_tasks': tasks_data
            }, room=request.sid)
            
            return {'status': 'success', 'message': 'Task completed successfully'}
            
        return {'status': 'error', 'message': 'Task must be in progress to finish'}
        
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
        ).first()
        
        if not student_task:
            return {'status': 'error', 'message': 'Task not found'}
        
        if student_task.status != StudentTask.STATUS_COMPLETED:
            student_task.status = StudentTask.STATUS_SKIPPED
            student_task.skipped_at = datetime.now(pytz.UTC)
            student_task.started_at = None
            student_task.finished_at = None
            
            db.session.commit()
            
            # Get next incomplete tasks after skipping
            task = Task.query.get(task_id)
            next_tasks = Task.query.outerjoin(
                StudentTask,
                (Task.id == StudentTask.task_id) & 
                (StudentTask.student_id == current_user.id)
            ).filter(
                Task.curriculum_id == task.curriculum_id,
                (StudentTask.status.is_(None)) |
                (StudentTask.status.in_([StudentTask.STATUS_NOT_STARTED]))
            ).order_by(Task.position).limit(10).all()
            
            # Format tasks for response
            tasks_data = [{
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'link': task.link
            } for task in next_tasks]
            
            socketio.emit('task_updated', {
                'task_id': task_id,
                'status': StudentTask.STATUS_SKIPPED,
                'next_tasks': tasks_data
            }, room=request.sid)
            
            return {'status': 'success', 'message': 'Task skipped successfully'}
            
        return {'status': 'error', 'message': 'Completed tasks cannot be skipped'}
        
    except Exception as e:
        logger.error(f'Error skipping task: {str(e)}')
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}
