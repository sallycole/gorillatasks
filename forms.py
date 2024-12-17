from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, IntegerField, DateField, SelectField
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
    public = BooleanField('Public')
    publisher = StringField('Publisher')
    grade_levels = SelectField('Grade Level', coerce=int)

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
