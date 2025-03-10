import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from flask_login import current_user
from app import socketio, db
from models import Task, StudentTask
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    if current_user.is_authenticated:
        logger.info(f"Authenticated user connected: {current_user.id} ({current_user.email})")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('start_task')
def handle_start_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    task_id = data.get('task_id')
    if not task_id:
        return {'status': 'error', 'message': 'Task ID is required'}

    try:
        from models import StudentTask

        # Reset any other in-progress tasks
        StudentTask.query.filter_by(
            student_id=current_user.id,
            status=StudentTask.STATUS_IN_PROGRESS
        ).update({
            "status": StudentTask.STATUS_NOT_STARTED,
            "started_at": None
        })

        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()

        if not student_task:
            return {'status': 'error', 'message': 'Task not found'}

        student_task.start()
        db.session.commit()

        # Emit an event to update the UI
        socketio.emit('task_updated', {
            'task_id': task_id,
            'status': student_task.status,
            'link': student_task.task.link
        }, room=request.sid)

        return {'status': 'success', 'message': 'Task started successfully'}
    except Exception as e:
        logger.error(f"Error starting task {task_id}: {str(e)}")
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@socketio.on('skip_task')
def handle_skip_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    task_id = data.get('task_id')
    if not task_id:
        return {'status': 'error', 'message': 'Task ID is required'}

    try:
        from models import StudentTask

        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()

        if not student_task:
            return {'status': 'error', 'message': 'Task not found'}

        if student_task.can_skip:
            student_task.skip()
            db.session.commit()

            # Emit an event to update the UI
            socketio.emit('task_updated', {
                'task_id': task_id,
                'status': student_task.status
            }, room=request.sid)

            return {'status': 'success', 'message': 'Task skipped successfully'}
        else:
            return {'status': 'error', 'message': 'Task cannot be skipped'}
    except Exception as e:
        logger.error(f"Error skipping task {task_id}: {str(e)}")
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@socketio.on('finish_task')
def handle_finish_task(data):
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required'}

    task_id = data.get('task_id')
    if not task_id:
        return {'status': 'error', 'message': 'Task ID is required'}

    try:
        from models import StudentTask

        student_task = StudentTask.query.filter_by(
            student_id=current_user.id,
            task_id=task_id
        ).first()

        if not student_task:
            return {'status': 'error', 'message': 'Task not found'}

        if student_task.can_finish:
            student_task.finish()
            db.session.commit()

            # Emit an event to update the UI
            socketio.emit('task_updated', {
                'task_id': task_id,
                'status': student_task.status
            }, room=request.sid)

            return {'status': 'success', 'message': 'Task finished successfully'}
        else:
            return {'status': 'error', 'message': 'Task cannot be finished'}
    except Exception as e:
        logger.error(f"Error finishing task {task_id}: {str(e)}")
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}