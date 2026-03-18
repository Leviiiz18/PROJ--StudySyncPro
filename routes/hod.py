from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Course, Specialization, Subject, Enrollment
from flask_bcrypt import Bcrypt

hod_bp = Blueprint('hod', __name__)
bcrypt = Bcrypt()

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'hod':
            flash('Access Denied', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@hod_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    dept = current_user.department
    stats = {
        'students': User.query.filter_by(role='student', department=dept).count(),
        'faculty': User.query.filter_by(role='faculty', department=dept).count(),
        'courses': Course.query.filter_by(department=dept).count(),
        'subjects': Subject.query.join(Course).filter(Course.department == dept).count()
    }
    recent_students = User.query.filter_by(role='student', department=dept).order_by(User.id.desc()).limit(5).all()
    recent_faculty = User.query.filter_by(role='faculty', department=dept).order_by(User.id.desc()).limit(5).all()
    
    # Fetch recent notifications (events)
    from models import Event
    notifications = Event.query.filter(
        (Event.created_by == current_user.id) | (Event.target_role == 'all')
    ).order_by(Event.date.desc()).limit(5).all()
    
    return render_template('hod_dashboard.html', stats=stats, recent_students=recent_students, recent_faculty=recent_faculty, notifications=notifications)

@hod_bp.route('/calendar')
@login_required
@admin_required
def calendar():
    return render_template('hod_calendar.html')

@hod_bp.route('/courses', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_courses():
    dept = current_user.department
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            new_course = Course(name=name, department=dept)
            db.session.add(new_course)
            db.session.commit()
            flash('Course added successfully!', 'success')
        else:
            flash('Please fill all fields', 'warning')
            
    courses = Course.query.filter_by(department=dept).all()
    return render_template('hod_manage.html', type='courses', data=courses)

@hod_bp.route('/specializations', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_specializations():
    dept = current_user.department
    if request.method == 'POST':
        name = request.form.get('name')
        course_id = request.form.get('course_id')
        # Integrity check
        course = Course.query.filter_by(id=course_id, department=dept).first()
        if name and course:
            new_spec = Specialization(name=name, course_id=course_id)
            db.session.add(new_spec)
            db.session.commit()
            flash('Specialization added successfully!', 'success')
            
    specializations = Specialization.query.join(Course).filter(Course.department == dept).all()
    courses = Course.query.filter_by(department=dept).all()
    return render_template('hod_manage.html', type='specializations', data=specializations, courses=courses)

@hod_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_subjects():
    dept = current_user.department
    if request.method == 'POST':
        name = request.form.get('name')
        course_id = request.form.get('course_id')
        spec_id = request.form.get('specialization_id')
        faculty_id = request.form.get('faculty_id')
        
        course = Course.query.filter_by(id=course_id, department=dept).first()
        if name and course:
            new_subject = Subject(name=name, course_id=course_id, specialization_id=spec_id, faculty_id=faculty_id)
            db.session.add(new_subject)
            db.session.commit()
            flash('Subject added successfully!', 'success')
            
    subjects = Subject.query.join(Course).filter(Course.department == dept).all()
    courses = Course.query.filter_by(department=dept).all()
    specializations = Specialization.query.join(Course).filter(Course.department == dept).all()
    faculty = User.query.filter_by(role='faculty', department=dept).all()
    return render_template('hod_manage.html', type='subjects', data=subjects, courses=courses, specializations=specializations, faculty=faculty)

@hod_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_users():
    dept = current_user.department
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(name=name, email=email, password=hashed_pw, role=role, department=dept)
            db.session.add(new_user)
            db.session.commit()
            flash(f'{role.capitalize()} user added successfully!', 'success')
            
    faculty = User.query.filter_by(role='faculty', department=dept).all()
    students = User.query.filter_by(role='student', department=dept).all()
    return render_template('hod_manage.html', type='users', faculty=faculty, students=students, courses=Course.query.filter_by(department=dept).all(), specializations=Specialization.query.join(Course).filter(Course.department == dept).all())

@hod_bp.route('/directory/faculty')
@login_required
@admin_required
def view_faculty():
    dept = current_user.department
    faculty = User.query.filter_by(role='faculty', department=dept).all()
    return render_template('hod_users_list.html', type='faculty', items=faculty, courses=Course.query.filter_by(department=dept).all(), specializations=Specialization.query.join(Course).filter(Course.department == dept).all())

@hod_bp.route('/directory/students')
@login_required
@admin_required
def view_students():
    dept = current_user.department
    students = User.query.filter_by(role='student', department=dept).all()
    return render_template('hod_users_list.html', type='students', items=students, courses=Course.query.filter_by(department=dept).all(), specializations=Specialization.query.join(Course).filter(Course.department == dept).all())

@hod_bp.route('/edit/<string:type>/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_item(type, id):
    dept = current_user.department
    if type == 'course':
        item = Course.query.filter_by(id=id, department=dept).first_or_404()
        item.name = request.form.get('name')
    elif type == 'specialization':
        item = Specialization.query.join(Course).filter(Specialization.id == id, Course.department == dept).first_or_404()
        item.name = request.form.get('name')
        item.course_id = request.form.get('course_id')
    elif type == 'subject':
        item = Subject.query.join(Course).filter(Subject.id == id, Course.department == dept).first_or_404()
        item.name = request.form.get('name')
        item.course_id = request.form.get('course_id')
        item.specialization_id = request.form.get('specialization_id')
        item.faculty_id = request.form.get('faculty_id')
    elif type == 'user':
        item = User.query.filter_by(id=id, department=dept).first_or_404()
        item.name = request.form.get('name')
        item.email = request.form.get('email')
        if request.form.get('password'):
            item.password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
    
    db.session.commit()
    flash('Updated successfully!', 'success')
    return redirect(request.referrer)

@hod_bp.route('/delete/<string:type>/<int:id>')
@login_required
@admin_required
def delete_item(type, id):
    dept = current_user.department
    if type == 'course':
        item = Course.query.filter_by(id=id, department=dept).first_or_404()
    elif type == 'specialization':
        item = Specialization.query.join(Course).filter(Specialization.id == id, Course.department == dept).first_or_404()
    elif type == 'subject':
        item = Subject.query.join(Course).filter(Subject.id == id, Course.department == dept).first_or_404()
    elif type == 'user':
        item = User.query.filter_by(id=id, department=dept).first_or_404()
    else:
        return redirect(url_for('hod.dashboard'))
        
    db.session.delete(item)
    db.session.commit()
    flash(f'Deleted successfully!', 'success')
    return redirect(request.referrer)

@hod_bp.route('/create_event', methods=['POST'])
@login_required
@admin_required
def create_event():
    from datetime import datetime
    title = request.form.get('title')
    description = request.form.get('description')
    event_date = request.form.get('date')
    target = request.form.get('target_role')
    
    if title and event_date and target:
        new_event = Event(
            title=title,
            description=description,
            date=datetime.strptime(event_date, '%Y-%m-%d').date(),
            created_by=current_user.id,
            target_role=target
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Event/Notification created successfully!', 'success')
    else:
        flash('Please fill required fields', 'warning')
    return redirect(request.referrer)
