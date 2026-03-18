from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, User, Specialization, Subject, Module, Unit, File, Event, Enrollment
from werkzeug.utils import secure_filename
import os
from datetime import datetime

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'faculty':
        return redirect(url_for('index'))
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    # Prepare enrollment data for each subject
    subject_details = []
    for sub in subjects:
        enrollments = Enrollment.query.filter_by(subject_id=sub.id).all()
        students = [en.student for en in enrollments]
        subject_details.append({
            'subject': sub,
            'students': students
        })
    
    # Fetch recent notifications
    from models import Event
    notifications = Event.query.filter(
        (Event.created_by == current_user.id) | 
        (Event.target_role.in_(['faculty', 'all']))
    ).order_by(Event.date.desc()).limit(5).all()

    return render_template('faculty_dashboard.html', subjects=subjects, subject_details=subject_details, notifications=notifications)

@faculty_bp.route('/calendar')
@login_required
def calendar():
    if current_user.role != 'faculty':
        return redirect(url_for('index'))
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    return render_template('faculty_calendar.html', subjects=subjects)

@faculty_bp.route('/my_students')
@login_required
def my_students():
    if current_user.role != 'faculty':
        return redirect(url_for('index'))
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    subject_details = []
    for sub in subjects:
        enrollments = Enrollment.query.filter_by(subject_id=sub.id).all()
        students = [en.student for en in enrollments]
        subject_details.append({
            'subject': sub,
            'students': students
        })
    return render_template('faculty_students.html', subject_details=subject_details)

@faculty_bp.route('/subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def manage_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if subject.faculty_id != current_user.id:
        flash('Access Denied', 'danger')
        return redirect(url_for('faculty.dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_module':
            title = request.form.get('title')
            new_module = Module(title=title, subject_id=subject_id)
            db.session.add(new_module)
            db.session.commit()
            flash('Module added!', 'success')
        elif action == 'add_unit':
            title = request.form.get('title')
            module_id = request.form.get('module_id')
            new_unit = Unit(title=title, module_id=module_id)
            db.session.add(new_unit)
            db.session.commit()
            flash('Unit added!', 'success')
            
    return render_template('faculty_subject.html', subject=subject)

@faculty_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    unit_id = request.form.get('unit_id')
    uploaded_file = request.files.get('file')
    
    if uploaded_file and unit_id:
        filename = secure_filename(uploaded_file.filename)
        # Create subject-specific folder for organization
        unit = Unit.query.get(unit_id)
        subject_name = unit.module.subject.name.replace(' ', '_')
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subject_name)
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        full_path = os.path.join(save_path, filename)
        uploaded_file.save(full_path)
        
        new_file = File(
            unit_id=unit_id,
            filename=filename,
            filepath=os.path.join(subject_name, filename),
            filetype=filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
        )
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully!', 'success')
        
    return redirect(request.referrer)


@faculty_bp.route('/create_event', methods=['POST'])
@login_required
def create_event():
    from datetime import datetime
    title = request.form.get('title')
    description = request.form.get('description')
    event_date = request.form.get('date')
    subject_id = request.form.get('subject_id')
    is_personal = request.form.get('is_personal') == 'true'
    
    if title and event_date:
        new_event = Event(
            title=title,
            description=description,
            date=datetime.strptime(event_date, '%Y-%m-%d').date(),
            created_by=current_user.id,
            target_role='personal' if is_personal else 'student',
            subject_id=subject_id if (not is_personal and subject_id) else None,
            user_id=current_user.id if is_personal else None
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Event/Reminder created!', 'success')
    return redirect(request.referrer)
