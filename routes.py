from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User, Profile, Curriculum, Task, StudentTask, Enrollment, WeeklySnapshot
from forms import (LoginForm, RegisterForm, ProfileForm, CurriculumForm, TaskForm, 
                  EnrollmentForm)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import pytz

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Auth routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
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
        
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Curriculum routes
@curriculum_bp.route('/')
@login_required
def list():
    curriculums = Curriculum.query.filter(
        (Curriculum.public == True) | (Curriculum.creator_id == current_user.id)
    ).all()
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
            publisher=form.publisher.data,
            published_at=datetime.utcnow()
        )
        db.session.add(curriculum)
        db.session.commit()
        return redirect(url_for('curriculum.list'))
    return render_template('curriculum/edit.html', form=form)

@curriculum_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    curriculum = Curriculum.query.get_or_404(id)
    if curriculum.creator_id != current_user.id:
        flash('Unauthorized')
        return redirect(url_for('curriculum.list'))
        
    form = CurriculumForm(obj=curriculum)
    if form.validate_on_submit():
        curriculum.name = form.name.data
        curriculum.description = form.description.data
        curriculum.link = form.link.data
        curriculum.public = form.public.data
        curriculum.publisher = form.publisher.data
        db.session.commit()
        return redirect(url_for('curriculum.list'))
    return render_template('curriculum/edit.html', form=form, curriculum=curriculum)

# Dashboard routes
@dashboard_bp.route('/')
@login_required
def index():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    snapshots = WeeklySnapshot.query.filter_by(
        student_id=current_user.id
    ).order_by(WeeklySnapshot.week_ending.desc()).limit(4).all()
    
    return render_template('dashboard/student.html', 
                         enrollments=enrollments,
                         snapshots=snapshots)

@dashboard_bp.route('/task/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_task(id):
    student_task = StudentTask.query.filter_by(
        student_id=current_user.id,
        task_id=id
    ).first_or_404()
    
    if student_task.status == 0:  # Not started
        student_task.status = 1  # In progress
        student_task.started_at = datetime.utcnow()
    elif student_task.status == 1:  # In progress
        student_task.status = 2  # Completed
        student_task.finished_at = datetime.utcnow()
        if student_task.started_at:
            delta = student_task.finished_at - student_task.started_at
            student_task.time_spent_minutes = int(delta.total_seconds() / 60)
    
    db.session.commit()
    return redirect(url_for('dashboard.index'))
