#!/usr/bin/env python3
"""
Gestion base de données SQLite
"""
import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='fileserver.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des fichiers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT DEFAULT 'admin'
            )
        ''')
        
        # Table des téléchargements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                user_ip TEXT,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Base de données initialisée")
    
    def add_file(self, filename, original_name, file_path, file_size):
        """Ajoute un fichier en DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO files (filename, original_name, file_path, file_size)
            VALUES (?, ?, ?, ?)
        ''', (filename, original_name, file_path, file_size))
        
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_id
    
    def get_all_files(self):
        """Récupère tous les fichiers"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Pour accès par nom colonne
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, original_name, file_size, upload_date
            FROM files ORDER BY upload_date DESC
        ''')
        
        files = cursor.fetchall()
        conn.close()
        return [dict(file) for file in files]
    
    def get_file_by_id(self, file_id):
        """Récupère un fichier par ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
        file = cursor.fetchone()
        conn.close()
        return dict(file) if file else None
    
    def log_download(self, file_id, user_ip):
        """Enregistre un téléchargement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO downloads (file_id, user_ip)
            VALUES (?, ?)
        ''', (file_id, user_ip))
        
        conn.commit()
        conn.close()
    
    def delete_file(self, file_id):
        """Supprime un fichier de la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer le chemin du fichier
        cursor.execute('SELECT file_path FROM files WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        
        if result:
            file_path = result[0]
            # Supprimer le fichier physique
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Supprimer de la DB
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            cursor.execute('DELETE FROM downloads WHERE file_id = ?', (file_id,))
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Initialiser la base de données
    db = DatabaseManager()
    print("🗄️ Base de données prête")