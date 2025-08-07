import configparser
from pathlib import Path
import os

class ConfigManager:
    _instance = None
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = Path('config/config.ini')
        self._ensure_config_exists()
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance
        
    def _ensure_config_exists(self):
        if not self.config_path.exists():
            self.config['FINGERPRINT'] = {
                'acoustid_min_confidence': '0.85',
                'spectral_similarity_threshold': '0.7',
                'musicbrainz_min_confidence': '0.7',
                'parallel_workers': '4'
            }
            self.config['BACKUP'] = {
                'database_path': 'backup/backup_history.db'
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                self.config.write(f)
        else:
            self.config.read(self.config_path)
    
    def get(self, section, key, fallback=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getfloat(self, section, key, fallback=None):
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getint(self, section, key, fallback=None):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section, key, fallback=None):
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section, key, value):
        """Définit une valeur de configuration"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        # Sauvegarder automatiquement
        self.save_config()
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier"""
        with open(self.config_path, 'w') as f:
            self.config.write(f)
