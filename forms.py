from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, BooleanField, 
    IntegerField, DateField, SelectField, SelectMultipleField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
import pytz

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
    
class CurriculumForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    link = StringField('Link')
    publisher = StringField('Publisher')
    grade_levels = SelectMultipleField('Grade Levels', choices=[
        ('K', 'Kindergarten'),
        ('1', '1st Grade'),
        ('2', '2nd Grade'),
        ('3', '3rd Grade'),
        ('4', '4th Grade'),
        ('5', '5th Grade'),
        ('6', '6th Grade'),
        ('7', '7th Grade'),
        ('8', '8th Grade'),
        ('9', '9th Grade'),
        ('10', '10th Grade'),
        ('11', '11th Grade'),
        ('12', '12th Grade'),
        ('College', 'College'),
        ('All', 'All Grades')
    ])

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    link = StringField('Link')
    action = SelectField('Action Type', coerce=int)
    position = IntegerField('Position')

class EnrollmentForm(FlaskForm):
    weekly_goal_count = IntegerField('Weekly Goal', validators=[DataRequired()])
    study_days_per_week = IntegerField('Study Days Per Week', validators=[Optional()])
    target_completion_date = DateField('Target Completion Date', validators=[Optional()])
