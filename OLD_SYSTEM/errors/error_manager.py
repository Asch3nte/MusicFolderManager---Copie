#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire centralisé des erreurs et messages pour MusicFolderManager
Applique les principes de la POO pour une architecture extensible et maintenable
"""

import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from .error_codes import ErrorCodes, ErrorInfo
from .exceptions import (
    MusicFolderManagerError, AudioProcessingError, ConfigurationError,
    FileAccessError, MetadataError, NetworkError, OrganizationError
)


class ErrorType(Enum):
    """Types d'erreurs pour classification"""
    CRITICAL = "critical"
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class MessageLevel(Enum):
    """Niveaux de messages pour le logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorManager:
    """Gestionnaire centralisé des erreurs et messages
    
    Utilise les principes de la POO :
    - Abstraction : Interface simple pour la gestion d'erreurs
    - Encapsulation : Détails internes cachés, API publique claire
    - Héritage : Extensible par sous-classement
    - Polymorphisme : Gestion uniforme de différents types d'erreurs
    """
    
    def __init__(self, logger_name: str = "MusicFolderManager"):
        """Initialise le gestionnaire d'erreurs
        
        Args:
            logger_name: Nom du logger pour cette instance
        """
        self.logger = logging.getLogger(logger_name)
        self.error_history: List[Dict] = []
        self.message_handlers: Dict[str, Callable] = {}
        self.statistics = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'last_error_time': None
        }
        
        # Configuration du logger si pas déjà configuré
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """Configure le logger par défaut"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def register_handler(self, handler_name: str, handler_func: Callable):
        """Enregistre un gestionnaire de messages personnalisé
        
        Permet l'extension du système de gestion d'erreurs (Polymorphisme)
        
        Args:
            handler_name: Nom unique du gestionnaire
            handler_func: Fonction appelée pour traiter les messages
        """
        self.message_handlers[handler_name] = handler_func
    
    def handle_error(self, error: Exception, context: Dict = None) -> Dict:
        """Gère une erreur de manière centralisée
        
        Args:
            error: Exception à traiter
            context: Contexte supplémentaire (fichier, operation, etc.)
            
        Returns:
            Dict avec les détails de traitement de l'erreur
        """
        context = context or {}
        
        # Déterminer le type d'erreur et le code approprié
        error_info = self._analyze_error(error, context)
        
        # Créer l'entrée d'historique
        error_entry = {
            'timestamp': time.time(),
            'error_type': error_info['type'],
            'error_code': error_info['code'],
            'message': error_info['user_message'],
            'technical_message': error_info['technical_message'],
            'context': context,
            'severity': error_info['severity']
        }
        
        # Ajouter à l'historique
        self.error_history.append(error_entry)
        
        # Mettre à jour les statistiques
        self._update_statistics(error_info)
        
        # Logger l'erreur
        self._log_error(error_entry)
        
        # Notifier les gestionnaires personnalisés
        self._notify_handlers(error_entry)
        
        return {
            'handled': True,
            'error_code': error_info['code'],
            'user_message': error_info['user_message'],
            'severity': error_info['severity'],
            'should_continue': error_info['severity'] in ['info', 'warning']
        }
    
    def _analyze_error(self, error: Exception, context: Dict) -> Dict:
        """Analyse une erreur pour déterminer le code et messages appropriés"""
        
        # Si c'est déjà une erreur de notre système
        if isinstance(error, MusicFolderManagerError):
            error_info = ErrorCodes.get_by_code(error.error_code)
            if error_info:
                return {
                    'type': type(error).__name__,
                    'code': error.error_code,
                    'user_message': error.get_user_message(),
                    'technical_message': str(error),
                    'severity': error_info.severity
                }
        
        # Analyser les erreurs système courantes
        error_str = str(error).lower()
        
        # Erreurs de fichiers
        if "no such file" in error_str or "file not found" in error_str:
            return {
                'type': 'FileAccessError',
                'code': ErrorCodes.FileAccess.FILE_NOT_FOUND.code,
                'user_message': f"Fichier introuvable: {context.get('file_path', 'inconnu')}",
                'technical_message': str(error),
                'severity': 'error'
            }
        
        # Erreurs de permissions
        if "permission denied" in error_str or "access denied" in error_str:
            return {
                'type': 'FileAccessError',
                'code': ErrorCodes.FileAccess.PERMISSION_DENIED.code,
                'user_message': ErrorCodes.FileAccess.PERMISSION_DENIED.user_message,
                'technical_message': str(error),
                'severity': 'error'
            }
        
        # Erreurs fpcalc
        if "fpcalc" in error_str:
            if "status 2" in error_str:
                return {
                    'type': 'AudioProcessingError',
                    'code': ErrorCodes.Audio.FILE_CORRUPTED.code,
                    'user_message': ErrorCodes.Audio.FILE_CORRUPTED.user_message,
                    'technical_message': str(error),
                    'severity': 'warning'
                }
            elif "status 1" in error_str:
                return {
                    'type': 'AudioProcessingError',
                    'code': ErrorCodes.Audio.FORMAT_UNSUPPORTED.code,
                    'user_message': ErrorCodes.Audio.FORMAT_UNSUPPORTED.user_message,
                    'technical_message': str(error),
                    'severity': 'warning'
                }
        
        # Erreurs de configuration
        if "no section" in error_str or "config" in error_str:
            return {
                'type': 'ConfigurationError',
                'code': ErrorCodes.Config.SECTION_MISSING.code,
                'user_message': ErrorCodes.Config.SECTION_MISSING.user_message,
                'technical_message': str(error),
                'severity': 'error'
            }
        
        # Erreurs réseau
        if "timeout" in error_str or "connection" in error_str:
            return {
                'type': 'NetworkError',
                'code': ErrorCodes.Network.CONNECTION_TIMEOUT.code,
                'user_message': ErrorCodes.Network.CONNECTION_TIMEOUT.user_message,
                'technical_message': str(error),
                'severity': 'warning'
            }
        
        # Erreur générique
        return {
            'type': 'GeneralError',
            'code': 'GENERAL_ERROR',
            'user_message': f"Erreur inattendue: {str(error)}",
            'technical_message': str(error),
            'severity': 'error'
        }
    
    def _update_statistics(self, error_info: Dict):
        """Met à jour les statistiques d'erreurs"""
        self.statistics['total_errors'] += 1
        self.statistics['last_error_time'] = time.time()
        
        # Par catégorie
        category = error_info.get('type', 'Unknown')
        self.statistics['errors_by_category'][category] = \
            self.statistics['errors_by_category'].get(category, 0) + 1
        
        # Par sévérité
        severity = error_info.get('severity', 'unknown')
        self.statistics['errors_by_severity'][severity] = \
            self.statistics['errors_by_severity'].get(severity, 0) + 1
    
    def _log_error(self, error_entry: Dict):
        """Log l'erreur selon sa sévérité"""
        message = f"[{error_entry['error_code']}] {error_entry['message']}"
        severity = error_entry['severity']
        
        if severity == 'critical':
            self.logger.critical(message)
        elif severity == 'error':
            self.logger.error(message)
        elif severity == 'warning':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def _notify_handlers(self, error_entry: Dict):
        """Notifie tous les gestionnaires enregistrés"""
        for handler_name, handler_func in self.message_handlers.items():
            try:
                handler_func(error_entry)
            except Exception as e:
                self.logger.error(f"Erreur dans le gestionnaire {handler_name}: {e}")
    
    def create_audio_error(self, message: str, file_path: str = None, 
                          fpcalc_status: int = None) -> AudioProcessingError:
        """Factory method pour créer des erreurs audio
        
        Facilite la création d'erreurs typées (Abstraction)
        """
        if fpcalc_status == 2:
            error_code = ErrorCodes.Audio.FILE_CORRUPTED.code
        elif fpcalc_status == 1:
            error_code = ErrorCodes.Audio.FORMAT_UNSUPPORTED.code
        else:
            error_code = ErrorCodes.Audio.PROCESSING_FAILED.code
        
        return AudioProcessingError(
            message=message,
            file_path=file_path,
            fpcalc_status=fpcalc_status,
            error_code=error_code
        )
    
    def create_config_error(self, message: str, section: str = None, 
                           key: str = None) -> ConfigurationError:
        """Factory method pour créer des erreurs de configuration"""
        if section:
            error_code = ErrorCodes.Config.SECTION_MISSING.code
        elif key:
            error_code = ErrorCodes.Config.KEY_MISSING.code
        else:
            error_code = ErrorCodes.Config.INVALID_VALUE.code
        
        return ConfigurationError(
            message=message,
            config_section=section,
            config_key=key,
            error_code=error_code
        )
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques d'erreurs"""
        return self.statistics.copy()
    
    def get_recent_errors(self, count: int = 10) -> List[Dict]:
        """Retourne les erreurs récentes"""
        return self.error_history[-count:] if self.error_history else []
    
    def clear_history(self):
        """Vide l'historique des erreurs"""
        self.error_history.clear()
        self.statistics = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'last_error_time': None
        }
    
    def format_user_message(self, error_code: str, **kwargs) -> str:
        """Formate un message utilisateur à partir d'un code d'erreur
        
        Args:
            error_code: Code d'erreur à formater
            **kwargs: Variables pour interpolation dans le message
            
        Returns:
            Message formaté pour l'utilisateur
        """
        error_info = ErrorCodes.get_by_code(error_code)
        if error_info:
            try:
                return error_info.user_message.format(**kwargs)
            except KeyError:
                return error_info.user_message
        
        return f"Erreur inconnue: {error_code}"


# Instance globale du gestionnaire d'erreurs (Singleton pattern)
_global_error_manager = None

def get_error_manager() -> ErrorManager:
    """Retourne l'instance globale du gestionnaire d'erreurs"""
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorManager()
    return _global_error_manager
