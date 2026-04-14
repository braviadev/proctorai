from flask_wtf import FlaskForm
from flask_wtf.file import FileField as WTFormsFileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, DecimalField, BooleanField, RadioField, SelectField, HiddenField
from wtforms.validators import DataRequired, ValidationError, NumberRange, Length
from wtforms.fields import DateField, TimeField
from datetime import datetime, timedelta

def validate_time_logic(form, field):
    if not (form.start_date.data and form.start_time.data and form.end_date.data and field.data):
        return
    try:
        start_dt_str = f"{form.start_date.data} {form.start_time.data}"
        end_dt_str = f"{form.end_date.data} {field.data}"
        start_date_time = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
        end_date_time = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M:%S")
        if start_date_time >= end_date_time:
            raise ValidationError("End date/time must not be earlier than or equal to start date/time.")
    except ValueError as e:
        raise ValidationError(f"Invalid date/time format: {e}")

class UploadForm(FlaskForm): # For Objective Tests
    subject = StringField('Subject', validators=[DataRequired()])
    topic = StringField('Topic', validators=[DataRequired()])
    doc = WTFormsFileField('CSV Upload', validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    start_date = DateField('Start Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    end_date = DateField('End Date', validators=[DataRequired()])
    end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    calc = BooleanField('Enable Calculator')
    neg_mark = DecimalField('Negative marking %', default=0.0, validators=[NumberRange(min=0, max=100)])
    duration = IntegerField('Duration(in min)', validators=[DataRequired(), NumberRange(min=1)])
    password = PasswordField('Exam Password', [DataRequired(), Length(min=3, max=10)])
    proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')], validators=[DataRequired()])

    def validate_end_time(self, field):
        validate_time_logic(self, field)

class QAUploadForm(FlaskForm): # For Subjective Tests
    subject = StringField('Subject', validators=[DataRequired()])
    topic = StringField('Topic', validators=[DataRequired()])
    doc = WTFormsFileField('CSV Upload', validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    start_date = DateField('Start Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    end_date = DateField('End Date', validators=[DataRequired()])
    end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    duration = IntegerField('Duration(in min)', validators=[DataRequired(), NumberRange(min=1)])
    password = PasswordField('Exam Password', [DataRequired(), Length(min=3, max=10)])
    proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')], validators=[DataRequired()])

    def validate_end_time(self, field):
        validate_time_logic(self, field)

class PracUploadForm(FlaskForm): # For Practical Tests
    subject = StringField('Subject', validators=[DataRequired()])
    topic = StringField('Topic', validators=[DataRequired()])
    questionprac = StringField('Question', validators=[DataRequired()])
    marksprac = IntegerField('Marks', validators=[DataRequired(), NumberRange(min=1)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    end_date = DateField('End Date', validators=[DataRequired()])
    end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5), format='%H:%M:%S')
    duration = IntegerField('Duration(in min)', validators=[DataRequired(), NumberRange(min=1)])
    compiler = SelectField(u'Compiler', choices=[('11', 'C'), ('116', 'Python 3x'), ('56', 'Node.js'), ('10', 'Java')], validators=[DataRequired()])
    password = PasswordField('Exam Password', [DataRequired(), Length(min=3, max=10)])
    proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')], validators=[DataRequired()])

    def validate_end_time(self, field):
        validate_time_logic(self, field)

class TestForm(FlaskForm): 
    test_id = StringField('Exam ID', validators=[DataRequired()])
    password = PasswordField('Exam Password', validators=[DataRequired()])
    img_hidden_form = HiddenField(label=(''))