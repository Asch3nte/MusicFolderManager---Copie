#!/usr/bin/env python3
"""
Gestionnaire SQLite simple pour le cache
"""

import sqlite3
import json
import time
import os
from pathlib import Path

class SQLiteCacheHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        # Créer le répertoire si nécessaire
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp REAL,
                    expiration REAL
                )
            ''')
            conn.commit()
    
    def get(self, key):
        """Récupère une valeur depuis le cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT data, expiration FROM cache WHERE key = ?',
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    data, expiration = result
                    # Vérifier l'expiration
                    if expiration is None or time.time() < expiration:
                        return json.loads(data)
                    else:
                        # Supprimer l'entrée expirée
                        conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                        conn.commit()
                
                return None
        except Exception:
            return None
    
    def set(self, key, data, expiration=None):
        """Stocke une valeur dans le cache"""
        try:
            timestamp = time.time()
            exp_time = timestamp + expiration if expiration else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO cache (key, data, timestamp, expiration) VALUES (?, ?, ?, ?)',
                    (key, json.dumps(data), timestamp, exp_time)
                )
                conn.commit()
        except Exception:
            pass  # Ignorer les erreurs de cache
    
    def clear(self):
        """Vide le cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM cache')
                conn.commit()
        except Exception:
            pass
    
    def cleanup_expired(self):
        """Nettoie les entrées expirées"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'DELETE FROM cache WHERE expiration IS NOT NULL AND expiration < ?',
                    (time.time(),)
                )
                conn.commit()
        except Exception:
            pass
