import sqlite3
import os
import hashlib

class AcoustIDCache:
    def __init__(self, db_path='acoustid_cache.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS fingerprints (
                file_hash TEXT PRIMARY KEY,
                audio_length REAL,
                fingerprint TEXT,
                timestamp REAL,
                track_id TEXT
            )''')
    
    def generate_file_hash(self, file_path):
        """Hash du fichier pour identifiant unique"""
        # Vérifier que le fichier existe avant d'accéder à sa date de modification
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
        
        return hashlib.sha256(file_path.encode() + str(os.path.getmtime(file_path)).encode()).hexdigest()

    def get(self, file_path):
        file_hash = self.generate_file_hash(file_path)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT audio_length, fingerprint, track_id FROM fingerprints WHERE file_hash = ?',
                (file_hash,)
            )
            return cursor.fetchone()

    def set(self, file_path, audio_length, fingerprint, track_id):
        file_hash = self.generate_file_hash(file_path)
        timestamp = os.path.getmtime(file_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO fingerprints 
                (file_hash, audio_length, fingerprint, timestamp, track_id) 
                VALUES (?, ?, ?, ?, ?)''',
                (file_hash, audio_length, fingerprint, timestamp, track_id)
            )
