from .sqlite_handler import SQLiteCacheHandler
import hashlib
import os
import functools
import configparser
from config.config_manager import ConfigManager

class CacheManager:
    _instance = None
    
    def __init__(self):
        if CacheManager._instance:
            raise RuntimeError("Utilisez CacheManager.get_instance()")
        
        config = ConfigManager.get_instance()
        
        # Gestion des valeurs par défaut manuellement
        try:
            cache_dir = config.get("GENERAL", "cache_dir")
        except (configparser.NoSectionError, configparser.NoOptionError):
            cache_dir = "cache"
            
        try:
            enabled_str = config.get("CACHE", "enabled").lower()
            self.enabled = enabled_str in ['true', '1', 'yes', 'on']
        except (configparser.NoSectionError, configparser.NoOptionError):
            self.enabled = True
            
        self.handler = SQLiteCacheHandler(f"{cache_dir}/cache_db.db")
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def generate_key(self, file_path: str, prefix: str = "fp_") -> str:
        """Génère une clé unique basée sur les méta-données du fichier"""
        stats = os.stat(file_path)
        unique_id = f"{file_path}-{stats.st_size}-{stats.st_mtime}"
        return prefix + hashlib.sha256(unique_id.encode()).hexdigest()
    
    def get_file_cache(self, file_path: str):
        """Récupère les données de cache pour un fichier"""
        if not self.enabled:
            return None
        key = self.generate_key(file_path)
        return self.handler.get(key)
    
    def set_file_cache(self, file_path: str, fingerprint_data: dict):
        """Stocke les données de fingerprint"""
        if not self.enabled:
            return
        key = self.generate_key(file_path)
        self.handler.set(key, fingerprint_data, expiration=3600 * 24 * 7)  # 1 semaine
    
    def caching(self, func):
        """Décorator pour ajouter du caching automatique à une fonction"""
        @functools.wraps(func)
        def wrapper(file_path, *args, **kwargs):
            # Tentative de récupération depuis le cache
            if cached := self.get_file_cache(file_path):
                return cached
            
            # Calcul au besoin
            result = func(file_path, *args, **kwargs)
            
            # Mise en cache
            self.set_file_cache(file_path, result)
            return result
        
        return wrapper
