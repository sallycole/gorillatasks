from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, BooleanField, 
    IntegerField, DateField, SelectField, SelectMultipleField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
import pytz
from models import GRADE_LEVELS

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password_confirmation = PasswordField('Confirm Password', 
                                      validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    time_zone = SelectField('Time Zone', choices=[(tz, tz) for tz in pytz.all_timezones])

class ProfileForm(FlaskForm):
    bio = TextAreaField('Bio')
    
from werkzeug.datastructures import FileStorage
from wtforms.fields import FileField

class CurriculumForm(FlaskForm):
    name = StringField('Name', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    link = StringField('Link', validators=[Optional()])
    publisher = StringField('Publisher', validators=[Optional()])
    xml_file = FileField('Upload XML Curriculum')
    grade_levels = SelectMultipleField('Grade Levels', choices=GRADE_LEVELS)

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    link = StringField('Link')
    action = SelectField('Action Type', coerce=int)
    position = IntegerField('Position')

class EnrollmentForm(FlaskForm):
    study_days_per_week = IntegerField('Study Days Per Week', validators=[DataRequired()])
    target_completion_date = DateField('Target Completion Date', validators=[DataRequired()])
