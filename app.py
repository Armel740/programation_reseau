#!/usr/bin/env python3
"""
Application Flask - Serveur de fichiers web avec Socket.IO
"""
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from database import DatabaseManager
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = '8fa29d2e17cb4bdb9a6b7c61a2bda8ea'
socketio = SocketIO(app, cors_allowed_origins="*")


UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'rar', 'mp4','mp3','mkv'}


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


db = DatabaseManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_file_size(size_bytes):
    """Formate la taille en format lisible"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024**2):.1f} MB"


@socketio.on('connect')
def handle_connect():
    print(f'Client connecté: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client déconnecté: {request.sid}')

@socketio.on('join_admin')
def handle_join_admin():
    if session.get('admin_logged_in'):
        join_room('admin')
        emit('status', {'message': 'Connecté au panel admin'})

@socketio.on('leave_admin')
def handle_leave_admin():
    leave_room('admin')


@app.route('/')
def index():
    """Page d'accueil - Liste des fichiers"""
    files = db.get_all_files()
    for file in files:
        file['formatted_size'] = format_file_size(file['file_size'])
    return render_template('index.html', files=files)

@app.route('/download/<int:file_id>')
def download_file(file_id):
    """Télécharge un fichier"""
    file_info = db.get_file_by_id(file_id)
    if not file_info:
        flash('Fichier non trouvé', 'error')
        return redirect(url_for('index'))
    
   
    db.log_download(file_id, request.remote_addr)
    
   
    socketio.emit('file_downloaded', {
        'filename': file_info['original_name'],
        'ip': request.remote_addr,
        'time': datetime.now().strftime('%H:%M:%S')
    }, room='admin')
    
    return send_file(
        file_info['file_path'],
        as_attachment=True,
        download_name=file_info['original_name']
    )

@app.route('/admin')
def admin():
    """Panel d'administration"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    files = db.get_all_files()
    for file in files:
        file['formatted_size'] = format_file_size(file['file_size'])
    
    return render_template('admin.html', files=files)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Connexion admin"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        
        if username == 'Armel' and password == 'armel740':
            session['admin_logged_in'] = True
            flash('Connexion réussie', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Identifiants incorrects', 'error')
    
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    """Déconnexion admin"""
    session.pop('admin_logged_in', None)
    flash('Déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/admin/upload', methods=['POST'])
def upload_file():
    """Upload de fichier (admin seulement)"""
    if not session.get('admin_logged_in'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('admin'))
    
    if file and allowed_file(file.filename):
      
        original_name = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_name}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
      
        file_id = db.add_file(unique_filename, original_name, file_path, file_size)
        
      
        file_data = {
            'id': file_id,
            'original_name': original_name,
            'formatted_size': format_file_size(file_size),
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        socketio.emit('file_added', file_data)
        socketio.emit('admin_notification', {
            'type': 'success',
            'message': f'Fichier "{original_name}" uploadé avec succès'
        }, room='admin')
        
        flash(f'Fichier "{original_name}" uploadé avec succès', 'success')
    else:
        flash('Type de fichier non autorisé', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:file_id>')
def delete_file(file_id):
    """Supprime un fichier (admin seulement)"""
    if not session.get('admin_logged_in'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    file_info = db.get_file_by_id(file_id)
    if file_info:
      
        try:
            os.remove(file_info['file_path'])
        except:
            pass
        
      
        db.delete_file(file_id)
        
       
        socketio.emit('file_deleted', {'file_id': file_id})
        socketio.emit('admin_notification', {
            'type': 'info',
            'message': f'Fichier "{file_info["original_name"]}" supprimé'
        }, room='admin')
        
        flash('Fichier supprimé', 'success')
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    print("🚀 Serveur de fichiers web démarré avec Socket.IO")
    print("👤 Admin: http://localhost:5000/admin (admin/admin123)")
    print("📁 Utilisateurs: http://localhost:5000")
    
 
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)