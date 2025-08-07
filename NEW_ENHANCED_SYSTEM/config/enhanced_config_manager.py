#!/usr/bin/env python3
"""
Gestionnaire de configuration moderne pour Enhanced Music Manager
"""

import configparser
import json
from pathlib import Path
from typing import Any, Dict, Optional

class EnhancedConfigManager:
    """Gestionnaire de configuration moderne avec support JSON et INI"""
    
    _instance = None
    
    def __init__(self):
        self.config_dir = Path(__file__).parent
        self.ini_config = configparser.ConfigParser()
        self.json_config = {}
        
        # Fichiers de configuration
        self.ini_path = self.config_dir / "enhanced_config.ini"
        self.json_path = self.config_dir / "enhanced_settings.json"
        
        self._load_configurations()
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = EnhancedConfigManager()
        return cls._instance
    
    def _load_configurations(self):
        """Charge les configurations depuis les fichiers"""
        self._load_ini_config()
        self._load_json_config()
    
    def _load_ini_config(self):
        """Charge la configuration INI"""
        if not self.ini_path.exists():
            self._create_default_ini()
        else:
            self.ini_config.read(self.ini_path)
    
    def _load_json_config(self):
        """Charge la configuration JSON"""
        if not self.json_path.exists():
            self._create_default_json()
        else:
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.json_config = json.load(f)
            except Exception:
                self._create_default_json()
    
    def _create_default_ini(self):
        """Crée la configuration INI par défaut"""
        self.ini_config['APIS'] = {
            'acoustid_api_key': '',
            'musicbrainz_user_agent': 'EnhancedMusicManager/1.0'
        }
        
        self.ini_config['ANALYSIS'] = {
            'acoustid_min_confidence': '0.85',
            'spectral_similarity_threshold': '0.7',
            'musicbrainz_min_confidence': '0.7',
            'parallel_workers': '4',
            'analysis_timeout': '30'
        }
        
        self.ini_config['PROCESSING'] = {
            'skip_corrupted_files': 'True',
            'enable_manual_selection': 'True',
            'auto_backup': 'True',
            'max_file_size_mb': '500'
        }
        
        self.ini_config['CACHE'] = {
            'enable_deep_cache': 'True',
            'cache_expiry_days': '30',
            'max_cache_size_mb': '1000',
            'auto_cleanup': 'True'
        }
        
        self._save_ini_config()
    
    def _create_default_json(self):
        """Crée la configuration JSON par défaut"""
        self.json_config = {
            'ui': {
                'theme': 'default',
                'window_geometry': '1200x800',
                'remember_geometry': True,
                'show_advanced_options': False,
                'auto_refresh': True
            },
            'paths': {
                'last_source_directory': '',
                'last_destination_directory': '',
                'export_directory': 'exports',
                'temp_directory': 'temp'
            },
            'export': {
                'default_format': 'json',
                'include_metadata': True,
                'include_statistics': True,
                'auto_timestamp': True
            },
            'advanced': {
                'debug_mode': False,
                'log_level': 'INFO',
                'performance_monitoring': False,
                'memory_optimization': True
            }
        }
        
        self._save_json_config()
    
    def _save_ini_config(self):
        """Sauvegarde la configuration INI"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.ini_path, 'w') as f:
            self.ini_config.write(f)
    
    def _save_json_config(self):
        """Sauvegarde la configuration JSON"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.json_config, f, indent=2, ensure_ascii=False)
    
    # Méthodes pour configuration INI
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Récupère une valeur de configuration INI"""
        try:
            return self.ini_config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getfloat(self, section: str, key: str, fallback: float = None) -> float:
        """Récupère une valeur float de configuration INI"""
        try:
            return self.ini_config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """Récupère une valeur int de configuration INI"""
        try:
            return self.ini_config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section: str, key: str, fallback: bool = None) -> bool:
        """Récupère une valeur boolean de configuration INI"""
        try:
            return self.ini_config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section: str, key: str, value: Any):
        """Définit une valeur de configuration INI"""
        if not self.ini_config.has_section(section):
            self.ini_config.add_section(section)
        self.ini_config.set(section, key, str(value))
        self._save_ini_config()
    
    # Méthodes pour configuration JSON
    def get_json(self, *keys, fallback=None):
        """Récupère une valeur de configuration JSON"""
        current = self.json_config
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return fallback
    
    def set_json(self, *keys, value):
        """Définit une valeur de configuration JSON"""
        current = self.json_config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self._save_json_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Retourne toute la configuration"""
        return {
            'ini': dict(self.ini_config),
            'json': self.json_config
        }
