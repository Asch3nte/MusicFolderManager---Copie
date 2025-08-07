#!/usr/bin/env python3
"""
Système de backup basé sur une base de données SQLite
Ne duplique pas les fichiers, mais garde une trace des modifications
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path
import hashlib

class BackupDatabase:
    def __init__(self, db_path="backup_history.db"):
        """Initialise la base de données de backup"""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Crée la table si elle n'existe pas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    original_checksum TEXT,
                    operation TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata_before TEXT,
                    metadata_after TEXT,
                    notes TEXT
                )
            """)
            conn.commit()
    
    def record_operation(self, file_path, operation, metadata_before=None, metadata_after=None, notes=None):
        """Enregistre une opération dans la base de données"""
        try:
            # Calculer le checksum du fichier s'il existe
            checksum = None
            if os.path.exists(file_path):
                checksum = self._calculate_checksum(file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO file_history 
                    (file_path, original_checksum, operation, metadata_before, metadata_after, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    file_path,
                    checksum,
                    operation,
                    json.dumps(metadata_before) if metadata_before else None,
                    json.dumps(metadata_after) if metadata_after else None,
                    notes
                ))
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'enregistrement: {e}")
            return False
    
    def _calculate_checksum(self, file_path):
        """Calcule le checksum MD5 d'un fichier"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
    
    def get_file_history(self, file_path):
        """Récupère l'historique d'un fichier"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM file_history 
                WHERE file_path = ? 
                ORDER BY timestamp DESC
            """, (file_path,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recent_operations(self, limit=50):
        """Récupère les opérations récentes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM file_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def can_rollback(self, file_path):
        """Vérifie si un rollback est possible pour un fichier"""
        history = self.get_file_history(file_path)
        if not history:
            return False, "Aucun historique trouvé"
        
        if not os.path.exists(file_path):
            return False, "Le fichier n'existe plus"
        
        current_checksum = self._calculate_checksum(file_path)
        last_operation = history[0]
        
        if current_checksum == last_operation['original_checksum']:
            return False, "Le fichier n'a pas été modifié"
        
        return True, "Rollback possible"
    
    def get_statistics(self):
        """Retourne des statistiques sur les opérations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    operation,
                    COUNT(*) as count,
                    MAX(timestamp) as last_operation
                FROM file_history 
                GROUP BY operation
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'count': row[1],
                    'last_operation': row[2]
                }
            
            # Total d'opérations
            cursor = conn.execute("SELECT COUNT(*) FROM file_history")
            total = cursor.fetchone()[0]
            stats['total'] = total
            
            return stats

# Instance globale
_backup_db = None

def get_backup_database():
    """Retourne l'instance de la base de données de backup"""
    global _backup_db
    if _backup_db is None:
        backup_dir = Path(__file__).parent
        db_path = backup_dir / "backup_history.db"
        _backup_db = BackupDatabase(str(db_path))
    return _backup_db

def record_file_operation(file_path, operation, metadata_before=None, metadata_after=None, notes=None):
    """Fonction utilitaire pour enregistrer une opération"""
    db = get_backup_database()
    return db.record_operation(file_path, operation, metadata_before, metadata_after, notes)
