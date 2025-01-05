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
    STANDARD_TIMEZONES = [
        ('Etc/GMT+12', 'IDLW'),  # International Date Line West
        ('Etc/GMT+11', 'NT'),    # Nome Time
        ('Etc/GMT+10', 'HST'),   # Hawaii Standard Time
        ('Etc/GMT+9', 'AKST'),   # Alaska Standard Time
        ('Etc/GMT+8', 'PST'),    # Pacific Standard Time
        ('Etc/GMT+7', 'MST'),    # Mountain Standard Time
        ('Etc/GMT+6', 'CST'),    # Central Standard Time
        ('Etc/GMT+5', 'EST'),    # Eastern Standard Time
        ('Etc/GMT+4', 'AST'),    # Atlantic Standard Time
        ('Etc/GMT+3', 'BRT'),    # Brazil Time
        ('Etc/GMT+2', 'AT'),     # Azores Time
        ('Etc/GMT+1', 'WAT'),    # West Africa Time
        ('Etc/GMT+0', 'GMT'),    # Greenwich Mean Time
        ('Etc/GMT-1', 'CET'),    # Central European Time
        ('Etc/GMT-2', 'EET'),    # Eastern European Time
        ('Etc/GMT-3', 'MSK'),    # Moscow Time
        ('Etc/GMT-4', 'GST'),    # Gulf Standard Time
        ('Etc/GMT-5', 'PKT'),    # Pakistan Time
        ('Etc/GMT-6', 'BST'),    # Bangladesh Standard Time
        ('Etc/GMT-7', 'ICT'),    # Indochina Time
        ('Etc/GMT-8', 'CST'),    # China Standard Time
        ('Etc/GMT-9', 'JST'),    # Japan Standard Time
        ('Etc/GMT-10', 'AEST'),  # Australian Eastern Standard Time
        ('Etc/GMT-11', 'AEDT'),  # Australian Eastern Daylight Time
        ('Etc/GMT-12', 'NZST'),  # New Zealand Standard Time
    ]
    time_zone = SelectField('Time Zone', choices=STANDARD_TIMEZONES)

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
