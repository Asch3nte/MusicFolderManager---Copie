#!/usr/bin/env python3
"""
Cache intelligent pour éliminer les quotas API
Système de cache SQLite multi-niveaux pour MusicBrainz et AcousticID
"""

import sqlite3
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Any

class IntelligentCache:
    """Cache intelligent pour requêtes API avec persistence SQLite"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Fichiers de cache séparés par type
        self.db_paths = {
            'fingerprints': self.cache_dir / "fingerprints.db",
            'musicbrainz': self.cache_dir / "musicbrainz.db", 
            'acousticid': self.cache_dir / "acousticid.db",
            'spectral': self.cache_dir / "spectral.db",
            'file_hashes': self.cache_dir / "file_hashes.db"
        }
        
        self._init_databases()
    
    def _init_databases(self):
        """Initialise les bases de données SQLite"""
        
        # Cache des fingerprints audio
        with sqlite3.connect(self.db_paths['fingerprints']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT,
                    fingerprint TEXT,
                    duration REAL,
                    format TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Cache MusicBrainz
        with sqlite3.connect(self.db_paths['musicbrainz']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS musicbrainz_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_type TEXT,
                    query_data TEXT,
                    response_data TEXT,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Cache AcousticID
        with sqlite3.connect(self.db_paths['acousticid']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS acousticid_cache (
                    fingerprint_hash TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    duration REAL,
                    response_data TEXT,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Cache des analyses spectrales
        with sqlite3.connect(self.db_paths['spectral']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spectral_cache (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT,
                    features_data TEXT,
                    analysis_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Cache des hash de fichiers
        with sqlite3.connect(self.db_paths['file_hashes']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    file_size INTEGER,
                    file_mtime REAL,
                    last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def get_file_hash(self, file_path: str) -> str:
        """Calcule ou récupère le hash d'un fichier"""
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        file_stat = path.stat()
        file_size = file_stat.st_size
        file_mtime = file_stat.st_mtime
        
        # Vérifier si le hash est en cache et toujours valide
        with sqlite3.connect(self.db_paths['file_hashes']) as conn:
            cursor = conn.execute("""
                SELECT file_hash FROM file_hashes 
                WHERE file_path = ? AND file_size = ? AND file_mtime = ?
            """, (str(file_path), file_size, file_mtime))
            
            cached_hash = cursor.fetchone()
            if cached_hash:
                return cached_hash[0]
        
        # Calculer le hash (optimisé pour gros fichiers)
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Lire par chunks pour économiser la mémoire
            while chunk := f.read(8192):
                hash_md5.update(chunk)
        
        file_hash = hash_md5.hexdigest()
        
        # Stocker en cache
        with sqlite3.connect(self.db_paths['file_hashes']) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_hashes 
                (file_path, file_hash, file_size, file_mtime)
                VALUES (?, ?, ?, ?)
            """, (str(file_path), file_hash, file_size, file_mtime))
        
        return file_hash
    
    def cache_fingerprint(self, file_path: str, fingerprint: str, duration: float, format_type: str):
        """Met en cache un fingerprint audio"""
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return False
        
        with sqlite3.connect(self.db_paths['fingerprints']) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fingerprints 
                (file_hash, file_path, fingerprint, duration, format)
                VALUES (?, ?, ?, ?, ?)
            """, (file_hash, file_path, fingerprint, duration, format_type))
        
        return True
    
    def get_cached_fingerprint(self, file_path: str) -> Optional[Dict]:
        """Récupère un fingerprint en cache"""
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return None
        
        with sqlite3.connect(self.db_paths['fingerprints']) as conn:
            cursor = conn.execute("""
                SELECT fingerprint, duration, format FROM fingerprints 
                WHERE file_hash = ?
            """, (file_hash,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'fingerprint': result[0],
                    'duration': result[1],
                    'format': result[2]
                }
        
        return None
    
    def cache_musicbrainz_response(self, query_type: str, query_data: Dict, response_data: Dict, success: bool = True):
        """Met en cache une réponse MusicBrainz"""
        query_str = json.dumps(query_data, sort_keys=True)
        query_hash = hashlib.sha256(query_str.encode()).hexdigest()
        
        with sqlite3.connect(self.db_paths['musicbrainz']) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO musicbrainz_cache 
                (query_hash, query_type, query_data, response_data, success)
                VALUES (?, ?, ?, ?, ?)
            """, (query_hash, query_type, query_str, json.dumps(response_data), success))
    
    def get_cached_musicbrainz_response(self, query_type: str, query_data: Dict) -> Optional[Dict]:
        """Récupère une réponse MusicBrainz en cache"""
        query_str = json.dumps(query_data, sort_keys=True)
        query_hash = hashlib.sha256(query_str.encode()).hexdigest()
        
        with sqlite3.connect(self.db_paths['musicbrainz']) as conn:
            cursor = conn.execute("""
                SELECT response_data, success FROM musicbrainz_cache 
                WHERE query_hash = ? AND query_type = ?
            """, (query_hash, query_type))
            
            result = cursor.fetchone()
            if result:
                return {
                    'data': json.loads(result[0]),
                    'success': result[1]
                }
        
        return None
    
    def cache_acousticid_response(self, fingerprint: str, duration: float, response_data: Dict, success: bool = True):
        """Met en cache une réponse AcousticID"""
        fingerprint_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        
        with sqlite3.connect(self.db_paths['acousticid']) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO acousticid_cache 
                (fingerprint_hash, fingerprint, duration, response_data, success)
                VALUES (?, ?, ?, ?, ?)
            """, (fingerprint_hash, fingerprint, duration, json.dumps(response_data), success))
    
    def get_cached_acousticid_response(self, fingerprint: str, duration: float) -> Optional[Dict]:
        """Récupère une réponse AcousticID en cache"""
        fingerprint_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        
        with sqlite3.connect(self.db_paths['acousticid']) as conn:
            cursor = conn.execute("""
                SELECT response_data, success FROM acousticid_cache 
                WHERE fingerprint_hash = ? AND ABS(duration - ?) < 1.0
            """, (fingerprint_hash, duration))
            
            result = cursor.fetchone()
            if result:
                return {
                    'data': json.loads(result[0]),
                    'success': result[1]
                }
        
        return None
    
    def cache_spectral_features(self, file_path: str, features: Dict, analysis_version: str = "v1.0"):
        """Met en cache des caractéristiques spectrales"""
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return False
        
        with sqlite3.connect(self.db_paths['spectral']) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO spectral_cache 
                (file_hash, file_path, features_data, analysis_version)
                VALUES (?, ?, ?, ?)
            """, (file_hash, file_path, json.dumps(features), analysis_version))
        
        return True
    
    def get_cached_spectral_features(self, file_path: str, analysis_version: str = "v1.0") -> Optional[Dict]:
        """Récupère des caractéristiques spectrales en cache"""
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return None
        
        with sqlite3.connect(self.db_paths['spectral']) as conn:
            cursor = conn.execute("""
                SELECT features_data FROM spectral_cache 
                WHERE file_hash = ? AND analysis_version = ?
            """, (file_hash, analysis_version))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
        
        return None
    
    def get_cache_statistics(self) -> Dict:
        """Retourne des statistiques sur le cache"""
        stats = {}
        
        for db_name, db_path in self.db_paths.items():
            with sqlite3.connect(db_path) as conn:
                # Compter les entrées
                tables = {
                    'fingerprints': 'fingerprints',
                    'musicbrainz': 'musicbrainz_cache',
                    'acousticid': 'acousticid_cache',
                    'spectral': 'spectral_cache',
                    'file_hashes': 'file_hashes'
                }
                
                if db_name in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {tables[db_name]}")
                    count = cursor.fetchone()[0]
                    
                    # Taille du fichier
                    size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
                    
                    stats[db_name] = {
                        'entries': count,
                        'size_mb': round(size_mb, 2)
                    }
        
        return stats
    
    def clear_cache(self, cache_type: str = None):
        """Vide le cache (tout ou un type spécifique)"""
        if cache_type and cache_type in self.db_paths:
            # Vider un cache spécifique
            db_path = self.db_paths[cache_type]
            if db_path.exists():
                db_path.unlink()
            self._init_databases()
        else:
            # Vider tous les caches
            for db_path in self.db_paths.values():
                if db_path.exists():
                    db_path.unlink()
            self._init_databases()

def test_cache_system():
    """Test du système de cache"""
    print("🧪 Test du système de cache intelligent")
    print("=" * 50)
    
    cache = IntelligentCache()
    
    # Test du cache de hash de fichier
    test_file = Path(__file__)
    file_hash = cache.get_file_hash(str(test_file))
    print(f"📁 Hash du fichier test: {file_hash[:16]}...")
    
    # Test du cache de fingerprint
    cache.cache_fingerprint(str(test_file), "test_fingerprint_12345", 180.5, "test")
    cached = cache.get_cached_fingerprint(str(test_file))
    print(f"🎵 Fingerprint en cache: {cached}")
    
    # Test du cache MusicBrainz
    query_data = {"artist": "Test Artist", "title": "Test Song"}
    response_data = {"mbid": "12345", "score": 0.95}
    cache.cache_musicbrainz_response("lookup", query_data, response_data)
    cached = cache.get_cached_musicbrainz_response("lookup", query_data)
    print(f"🎶 MusicBrainz en cache: {cached}")
    
    # Statistiques
    stats = cache.get_cache_statistics()
    print(f"\n📊 Statistiques du cache:")
    for db_name, db_stats in stats.items():
        print(f"   {db_name}: {db_stats['entries']} entrées, {db_stats['size_mb']}MB")

if __name__ == "__main__":
    test_cache_system()
