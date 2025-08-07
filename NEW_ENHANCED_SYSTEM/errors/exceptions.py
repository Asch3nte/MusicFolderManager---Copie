#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exceptions personnalisées pour MusicFolderManager
Hiérarchie d'exceptions spécialisées selon les domaines fonctionnels
"""

class MusicFolderManagerError(Exception):
    """Exception de base pour toutes les erreurs du MusicFolderManager
    
    Fournit l'abstraction de base pour toutes les erreurs du système.
    Permet l'encapsulation des détails d'erreur et facilite l'héritage.
    """
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        Args:
            message: Message d'erreur lisible par l'utilisateur
            error_code: Code d'erreur unique pour le diagnostic
            details: Détails supplémentaires pour le débogage
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.details = details or {}
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"
    
    def get_user_message(self) -> str:
        """Retourne un message adapté à l'utilisateur final"""
        return self.message
    
    def get_technical_details(self) -> dict:
        """Retourne les détails techniques pour le debugging"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }


class AudioProcessingError(MusicFolderManagerError):
    """Erreurs liées au traitement audio
    
    Hérite de MusicFolderManagerError et spécialise pour les erreurs audio.
    Encapsule les détails techniques du traitement audio.
    """
    
    def __init__(self, message: str, file_path: str = None, fpcalc_status: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.fpcalc_status = fpcalc_status
        
        # Enrichir les détails avec les informations audio
        self.details.update({
            'file_path': file_path,
            'fpcalc_status': fpcalc_status
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs audio"""
        if self.fpcalc_status == 1:
            return f"Format audio non supporté ou invalide: {self.file_path}"
        elif self.fpcalc_status == 2:
            return f"Fichier audio corrompu ou endommagé: {self.file_path}"
        else:
            return f"Erreur de traitement audio: {self.message}"


class ConfigurationError(MusicFolderManagerError):
    """Erreurs de configuration système
    
    Gère les erreurs liées à la configuration, sections manquantes, etc.
    """
    
    def __init__(self, message: str, config_section: str = None, config_key: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_section = config_section
        self.config_key = config_key
        
        self.details.update({
            'config_section': config_section,
            'config_key': config_key
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs de configuration"""
        if self.config_section:
            return f"Configuration manquante dans la section [{self.config_section}]: {self.message}"
        return f"Erreur de configuration: {self.message}"


class FileAccessError(MusicFolderManagerError):
    """Erreurs d'accès aux fichiers
    
    Encapsule les problèmes d'accès, permissions, fichiers manquants, etc.
    """
    
    def __init__(self, message: str, file_path: str = None, permission_issue: bool = False, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.permission_issue = permission_issue
        
        self.details.update({
            'file_path': file_path,
            'permission_issue': permission_issue
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs de fichiers"""
        if self.permission_issue:
            return f"Permissions insuffisantes pour accéder au fichier: {self.file_path}"
        elif self.file_path:
            return f"Fichier inaccessible: {self.file_path}"
        return f"Erreur d'accès aux fichiers: {self.message}"


class MetadataError(MusicFolderManagerError):
    """Erreurs de métadonnées
    
    Gère les problèmes liés aux métadonnées audio, API externes, etc.
    """
    
    def __init__(self, message: str, metadata_source: str = None, confidence: float = None, **kwargs):
        super().__init__(message, **kwargs)
        self.metadata_source = metadata_source
        self.confidence = confidence
        
        self.details.update({
            'metadata_source': metadata_source,
            'confidence': confidence
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs de métadonnées"""
        if self.metadata_source == 'acoustid':
            return f"Erreur lors de l'identification AcoustID: {self.message}"
        elif self.metadata_source == 'spectral':
            return f"Erreur lors de l'analyse spectrale: {self.message}"
        return f"Erreur de métadonnées: {self.message}"


class NetworkError(MusicFolderManagerError):
    """Erreurs réseau et API externes
    
    Gère les timeouts, erreurs d'API, problèmes de connectivité
    """
    
    def __init__(self, message: str, api_endpoint: str = None, status_code: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.api_endpoint = api_endpoint
        self.status_code = status_code
        
        self.details.update({
            'api_endpoint': api_endpoint,
            'status_code': status_code
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs réseau"""
        if self.status_code == 429:
            return "Limite de requêtes API atteinte. Veuillez patienter avant de réessayer."
        elif self.status_code == 401:
            return "Clé API invalide ou expirée. Vérifiez votre configuration."
        return f"Erreur de connexion: {self.message}"


class OrganizationError(MusicFolderManagerError):
    """Erreurs d'organisation de fichiers
    
    Gère les problèmes de déplacement, copie, création de dossiers
    """
    
    def __init__(self, message: str, source_path: str = None, destination_path: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.source_path = source_path
        self.destination_path = destination_path
        
        self.details.update({
            'source_path': source_path,
            'destination_path': destination_path
        })
    
    def get_user_message(self) -> str:
        """Message adapté pour les erreurs d'organisation"""
        if self.source_path and self.destination_path:
            return f"Impossible d'organiser le fichier de {self.source_path} vers {self.destination_path}: {self.message}"
        return f"Erreur d'organisation: {self.message}"
