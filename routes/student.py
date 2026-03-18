from flask import Blueprint, render_template, redirect, url_for, flash, send_from_directory, current_app, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Specialization, Subject, Enrollment, Module, Event, File
import os

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    # Fetch enrolled subjects for notifications
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subject_ids = [e.subject_id for e in enrollments]
    
    # Fetch recent notifications
    from models import Event
    notifications = Event.query.filter(
        (Event.target_role.in_(['student', 'all'])) |
        (Event.subject_id.in_(subject_ids)) |
        ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
    ).order_by(Event.date.desc()).limit(5).all()

    return render_template('student_dashboard.html', notifications=notifications)

@student_bp.route('/my_courses')
@login_required
def my_courses():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [e.subject for e in enrollments]
    return render_template('student_courses.html', subjects=subjects)

@student_bp.route('/subject/<int:subject_id>')
@login_required
def view_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    # Check enrollment
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, subject_id=subject_id).first()
    if not enrollment:
        flash('You are not enrolled in this subject', 'warning')
        return redirect(url_for('student.dashboard'))
        
    return render_template('student_subject.html', subject=subject)

@student_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file_record = File.query.get_or_404(file_id)
    # Check if student is enrolled in the subject this file belongs to
    subject = file_record.unit.module.subject
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, subject_id=subject.id).first()
    
    if not enrollment:
        flash('Access Denied', 'danger')
        return redirect(url_for('student.dashboard'))
        
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'], 
        file_record.filepath,
        as_attachment=False
    )

@student_bp.route('/calendar')
@login_required
def calendar():
    return render_template('student_calendar.html')

@student_bp.route('/create_personal_event', methods=['POST'])
@login_required
def create_personal_event():
    from datetime import datetime
    title = request.form.get('title')
    description = request.form.get('description')
    event_date = request.form.get('date')
    
    if title and event_date:
        new_event = Event(
            title=title,
            description=description,
            date=datetime.strptime(event_date, '%Y-%m-%d').date(),
            created_by=current_user.id,
            target_role='personal',
            user_id=current_user.id
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Personal reminder added!', 'success')
    return redirect(request.referrer)

@student_bp.route('/search-materials', methods=['POST'])
@login_required
def search_materials():
    try:
        data = request.get_json()
        if not data:
            return jsonify([])
            
        query = data.get('query', '').lower()
        if not query:
            return jsonify([])

        # Basic keywords extraction
        stopwords = {'what', 'is', 'how', 'to', 'the', 'a', 'an', 'and', 'for', 'of', 'in', 'on', 'with', 'about', 'who'}
        keywords = [w for w in query.split() if w not in stopwords]
        if not keywords:
            keywords = [query]

        # Get enrolled subjects
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        subject_ids = [e.subject_id for e in enrollments]
        
        results = []
        matching_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
        
        for sub in matching_subjects:
            score = 0
            if any(k in sub.name.lower() for k in keywords):
                score += 100
                
            for mod in sub.modules:
                mod_score = score
                if any(k in mod.title.lower() for k in keywords):
                    mod_score += 50
                    
                for unit in mod.units:
                    unit_score = mod_score
                    if any(k in unit.title.lower() for k in keywords):
                        unit_score += 25
                        
                    for file_rec in unit.files:
                        file_score = unit_score
                        if any(k in file_rec.filename.lower() for k in keywords):
                            file_score += 75
                        
                        if file_score > 0:
                            results.append({
                                'score': file_score,
                                'subject': sub.name,
                                'module': mod.title,
                                'unit': unit.title,
                                'file': file_rec.filename,
                                'file_id': file_rec.id,
                                'preview': f"Found in {sub.name} > {mod.title} > {unit.title}"
                            })

        results.sort(key=lambda x: x['score'], reverse=True)
        seen_files = set()
        final_results = []
        for r in results:
            if r['file_id'] not in seen_files:
                final_results.append(r)
                seen_files.add(r['file_id'])
                if len(final_results) >= 5:
                    break
                    
        return jsonify(final_results)
    except Exception as e:
        print(f"Search Error: {e}")
        return jsonify({"error": str(e)}), 500

@student_bp.route('/module/<int:module_id>/chat')
@login_required
def module_chat_page(module_id):
    module = Module.query.get_or_404(module_id)
    return render_template('student_module_chat.html', module=module)

@student_bp.route('/module-chat', methods=['POST'])
@login_required
def module_chat():
    from flask import jsonify, request
    import requests
    import json
    from rag_utils import get_embedding, get_similarity
    from models import DocumentChunk
    
    data = request.get_json()
    module_id = data.get('module_id')
    question = data.get('question')
    
    if not module_id or not question:
        return jsonify({"answer": "Invalid request"}), 400
        
    query_vec = get_embedding(question)
    chunks = DocumentChunk.query.filter_by(module_id=module_id).all()
    
    if not chunks:
        return jsonify({"answer": "No content available in this module to answer from."})
        
    ranked = []
    for c in chunks:
        try:
            sim = get_similarity(query_vec, json.loads(c.embedding))
            ranked.append((sim, c.content))
        except:
            continue
    
    ranked.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [x[1] for x in ranked[:5]]
    context = "\n\n".join(top_chunks)
    
    api_key = "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"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "StudySyncPro ERP"
    }
    
    prompt = {
        "model": "mistralai/mixtral-8x7b-instruct",
        "messages": [
            {
                "role": "system", 
                "content": "You are an academic assistant. Answer ONLY from the given context. If the answer is not in the context, say 'Not found in module content'."
            },
            {
                "role": "user", 
                "content": f"Question: {question}\n\nCONTEXT:\n{context}"
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=prompt
        )
        res_json = response.json()
        if 'choices' in res_json:
            answer = res_json['choices'][0]['message']['content']
        else:
            answer = f"Error from AI: {res_json.get('error', {}).get('message', 'Unknown Error')}"
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"answer": f"Connection Error: {str(e)}"}), 500
