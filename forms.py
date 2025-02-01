from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, BooleanField, 
    IntegerField, DateField, SelectField, SelectMultipleField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
import pytz
from models import GRADE_LEVELS

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password_confirmation = PasswordField('Confirm Password', 
                                      validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    STANDARD_TIMEZONES = [
        ('', 'Select Time Zone'),  # Default empty option
        ('Etc/GMT+12', 'IDLW (UTC-12)'),  # International Date Line West
        ('Etc/GMT+11', 'NT (UTC-11)'),    # Nome Time
        ('Etc/GMT+10', 'HST (UTC-10)'),   # Hawaii Standard Time
        ('Etc/GMT+9', 'AKST (UTC-9)'),   # Alaska Standard Time
        ('Etc/GMT+8', 'PST (UTC-8)'),    # Pacific Standard Time
        ('Etc/GMT+7', 'MST (UTC-7)'),    # Mountain Standard Time
        ('Etc/GMT+6', 'CST (UTC-6)'),    # Central Standard Time
        ('Etc/GMT+5', 'EST (UTC-5)'),    # Eastern Standard Time
        ('Etc/GMT+4', 'AST (UTC-4)'),    # Atlantic Standard Time
        ('Etc/GMT+3', 'BRT (UTC-3)'),    # Brazil Time
        ('Etc/GMT+2', 'AT (UTC-2)'),     # Azores Time
        ('Etc/GMT+1', 'WAT (UTC-1)'),    # West Africa Time
        ('Etc/GMT+0', 'GMT (UTC+0)'),    # Greenwich Mean Time
        ('Etc/GMT-1', 'CET (UTC+1)'),    # Central European Time
        ('Etc/GMT-2', 'EET (UTC+2)'),    # Eastern European Time
        ('Etc/GMT-3', 'MSK (UTC+3)'),    # Moscow Time
        ('Etc/GMT-4', 'GST (UTC+4)'),    # Gulf Standard Time
        ('Etc/GMT-5', 'PKT (UTC+5)'),    # Pakistan Time
        ('Etc/GMT-6', 'BST (UTC+6)'),    # Bangladesh Standard Time
        ('Etc/GMT-7', 'ICT (UTC+7)'),    # Indochina Time
        ('Etc/GMT-8', 'CNST (UTC+8)'),    # China Standard Time
        ('Etc/GMT-9', 'JST (UTC+9)'),    # Japan Standard Time
        ('Etc/GMT-10', 'AEST (UTC+10)'), # Australian Eastern Standard Time
        ('Etc/GMT-11', 'AEDT (UTC+11)'), # Australian Eastern Daylight Time
        ('Etc/GMT-12', 'NZST (UTC+12)'), # New Zealand Standard Time
    ]
    time_zone = SelectField('Time Zone', choices=STANDARD_TIMEZONES, validators=[DataRequired(message="Please select a time zone")])

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

class UserEditForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    time_zone = SelectField('Time Zone', choices=RegisterForm.STANDARD_TIMEZONES, validators=[DataRequired()])

class EnrollmentForm(FlaskForm):
    study_days_per_week = IntegerField('Study Days Per Week', validators=[DataRequired()])
    target_completion_date = DateField('Target Completion Date', validators=[DataRequired()])