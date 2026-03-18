from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # hod, faculty, student
    department = db.Column(db.String(100))
    
    # Relationships
    subjects_taught = db.relationship('Subject', backref='faculty', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    events_created = db.relationship('Event', backref='creator', lazy=True, foreign_keys='Event.created_by')
    personal_reminders = db.relationship('Event', backref='owner', lazy=True, foreign_keys='Event.user_id')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    specializations = db.relationship('Specialization', backref='course', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='course', lazy=True, cascade="all, delete-orphan")

class Specialization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    subjects = db.relationship('Subject', backref='specialization', lazy=True, cascade="all, delete-orphan")

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    specialization_id = db.Column(db.Integer, db.ForeignKey('specialization.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    modules = db.relationship('Module', backref='subject', lazy=True, cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', backref='subject', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='subject', lazy=True, cascade="all, delete-orphan")

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    units = db.relationship('Unit', backref='module', lazy=True, cascade="all, delete-orphan")

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    files = db.relationship('File', backref='unit', lazy=True, cascade="all, delete-orphan")

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # target control
    target_role = db.Column(db.String(20), nullable=False)  
    # values: "faculty", "student", "all", "personal"

    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # For personal reminders or direct target
    
    # Explicit relationship mapping to avoid ambiguity
    subject_rel = db.relationship('Subject', foreign_keys=[subject_id])
    user_rel = db.relationship('User', foreign_keys=[user_id])
    creator_rel = db.relationship('User', foreign_keys=[created_by])

class DocumentChunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text, nullable=False)  # JSON string of vector
