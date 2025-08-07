#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codes d'erreur centralisés pour MusicFolderManager
Utilise l'encapsulation pour organiser les codes par domaine fonctionnel
"""

from enum import Enum
from typing import Dict, NamedTuple


class ErrorInfo(NamedTuple):
    """Structure d'information d'erreur"""
    code: str
    category: str
    severity: str
    user_message: str
    technical_message: str


class ErrorCodes:
    """Gestionnaire centralisé des codes d'erreur
    
    Utilise l'encapsulation pour organiser les codes d'erreur par domaine.
    Facilite la maintenance et l'extension des codes d'erreur.
    """
    
    # === ERREURS AUDIO ===
    class Audio:
        """Codes d'erreur liés au traitement audio"""
        
        FILE_NOT_FOUND = ErrorInfo(
            code="AUDIO_001",
            category="audio",
            severity="error",
            user_message="Fichier audio introuvable",
            technical_message="Le fichier spécifié n'existe pas ou n'est pas accessible"
        )
        
        FILE_CORRUPTED = ErrorInfo(
            code="AUDIO_002", 
            category="audio",
            severity="warning",
            user_message="Fichier audio corrompu ou endommagé",
            technical_message="fpcalc a retourné le code de sortie 2 (fichier corrompu)"
        )
        
        FORMAT_UNSUPPORTED = ErrorInfo(
            code="AUDIO_003",
            category="audio", 
            severity="warning",
            user_message="Format audio non supporté",
            technical_message="fpcalc a retourné le code de sortie 1 (format invalide)"
        )
        
        FPCALC_NOT_FOUND = ErrorInfo(
            code="AUDIO_004",
            category="audio",
            severity="error", 
            user_message="Outil d'analyse audio manquant",
            technical_message="fpcalc.exe introuvable dans audio_tools/"
        )
        
        PROCESSING_FAILED = ErrorInfo(
            code="AUDIO_005",
            category="audio",
            severity="error",
            user_message="Échec du traitement audio",
            technical_message="Erreur interne lors du traitement audio"
        )
        
        FILE_TOO_SMALL = ErrorInfo(
            code="AUDIO_006",
            category="audio",
            severity="info",
            user_message="Fichier audio trop petit",
            technical_message="Taille du fichier inférieure au minimum requis"
        )
    
    # === ERREURS DE CONFIGURATION ===
    class Config:
        """Codes d'erreur liés à la configuration"""
        
        SECTION_MISSING = ErrorInfo(
            code="CONFIG_001",
            category="config",
            severity="error",
            user_message="Section de configuration manquante", 
            technical_message="Section requise absente du fichier config.ini"
        )
        
        KEY_MISSING = ErrorInfo(
            code="CONFIG_002",
            category="config",
            severity="error",
            user_message="Paramètre de configuration manquant",
            technical_message="Clé de configuration requise introuvable"
        )
        
        INVALID_VALUE = ErrorInfo(
            code="CONFIG_003",
            category="config",
            severity="error",
            user_message="Valeur de configuration invalide",
            technical_message="La valeur de configuration ne respecte pas le format attendu"
        )
        
        FILE_NOT_FOUND = ErrorInfo(
            code="CONFIG_004",
            category="config",
            severity="error",
            user_message="Fichier de configuration introuvable",
            technical_message="config.ini non trouvé dans le répertoire config/"
        )
    
    # === ERREURS D'ACCÈS FICHIERS ===
    class FileAccess:
        """Codes d'erreur liés à l'accès aux fichiers"""
        
        PERMISSION_DENIED = ErrorInfo(
            code="FILE_001",
            category="file_access",
            severity="error",
            user_message="Permissions insuffisantes",
            technical_message="Accès refusé pour lecture/écriture du fichier"
        )
        
        DIRECTORY_NOT_FOUND = ErrorInfo(
            code="FILE_002",
            category="file_access", 
            severity="error",
            user_message="Répertoire introuvable",
            technical_message="Le répertoire spécifié n'existe pas"
        )
        
        DISK_FULL = ErrorInfo(
            code="FILE_003",
            category="file_access",
            severity="error",
            user_message="Espace disque insuffisant",
            technical_message="Impossible d'écrire, disque plein"
        )
        
        FILE_LOCKED = ErrorInfo(
            code="FILE_004",
            category="file_access",
            severity="warning",
            user_message="Fichier en cours d'utilisation",
            technical_message="Fichier verrouillé par un autre processus"
        )
    
    # === ERREURS DE MÉTADONNÉES ===
    class Metadata:
        """Codes d'erreur liés aux métadonnées"""
        
        ACOUSTID_API_ERROR = ErrorInfo(
            code="META_001",
            category="metadata",
            severity="error",
            user_message="Erreur de l'API AcoustID",
            technical_message="Échec de la requête vers l'API AcoustID"
        )
        
        INVALID_API_KEY = ErrorInfo(
            code="META_002",
            category="metadata",
            severity="error",
            user_message="Clé API invalide",
            technical_message="La clé API AcoustID est invalide ou expirée"
        )
        
        LOW_CONFIDENCE = ErrorInfo(
            code="META_003",
            category="metadata",
            severity="info",
            user_message="Identification incertaine",
            technical_message="Confiance insuffisante dans l'identification"
        )
        
        NO_MATCHES = ErrorInfo(
            code="META_004",
            category="metadata",
            severity="info",
            user_message="Aucune correspondance trouvée",
            technical_message="Aucun résultat dans les bases de données"
        )
        
        SPECTRAL_ANALYSIS_FAILED = ErrorInfo(
            code="META_005",
            category="metadata",
            severity="warning",
            user_message="Échec de l'analyse spectrale",
            technical_message="Impossible d'analyser le spectre audio"
        )
    
    # === ERREURS RÉSEAU ===
    class Network:
        """Codes d'erreur liés au réseau et APIs"""
        
        CONNECTION_TIMEOUT = ErrorInfo(
            code="NET_001",
            category="network",
            severity="warning",
            user_message="Délai d'attente dépassé",
            technical_message="Timeout lors de la connexion à l'API"
        )
        
        API_RATE_LIMITED = ErrorInfo(
            code="NET_002",
            category="network",
            severity="warning",
            user_message="Limite de requêtes atteinte",
            technical_message="Trop de requêtes API, limitation appliquée"
        )
        
        NO_INTERNET = ErrorInfo(
            code="NET_003",
            category="network",
            severity="error",
            user_message="Connexion Internet requise",
            technical_message="Impossible de joindre les services externes"
        )
        
        SERVER_ERROR = ErrorInfo(
            code="NET_004",
            category="network",
            severity="error",
            user_message="Erreur du serveur distant",
            technical_message="Le serveur API a retourné une erreur"
        )
    
    # === ERREURS D'ORGANISATION ===
    class Organization:
        """Codes d'erreur liés à l'organisation des fichiers"""
        
        DESTINATION_EXISTS = ErrorInfo(
            code="ORG_001",
            category="organization",
            severity="warning",
            user_message="Fichier de destination existe déjà",
            technical_message="Un fichier avec ce nom existe dans le dossier de destination"
        )
        
        INVALID_PATTERN = ErrorInfo(
            code="ORG_002",
            category="organization",
            severity="error",
            user_message="Pattern de nommage invalide",
            technical_message="Le pattern contient des caractères interdits ou une syntaxe invalide"
        )
        
        COPY_FAILED = ErrorInfo(
            code="ORG_003",
            category="organization",
            severity="error",
            user_message="Échec de la copie de fichier",
            technical_message="Impossible de copier le fichier vers la destination"
        )
        
        MOVE_FAILED = ErrorInfo(
            code="ORG_004",
            category="organization",
            severity="error",
            user_message="Échec du déplacement de fichier",
            technical_message="Impossible de déplacer le fichier vers la destination"
        )
    
    @classmethod
    def get_all_codes(cls) -> Dict[str, ErrorInfo]:
        """Retourne tous les codes d'erreur disponibles
        
        Utilise la réflexion pour collecter automatiquement tous les codes
        définis dans les sous-classes.
        """
        codes = {}
        
        # Parcourir toutes les sous-classes
        for category_name in ['Audio', 'Config', 'FileAccess', 'Metadata', 'Network', 'Organization']:
            category = getattr(cls, category_name)
            
            # Parcourir tous les attributs de la catégorie
            for attr_name in dir(category):
                if not attr_name.startswith('_'):
                    error_info = getattr(category, attr_name)
                    if isinstance(error_info, ErrorInfo):
                        codes[error_info.code] = error_info
        
        return codes
    
    @classmethod
    def get_by_code(cls, code: str) -> ErrorInfo:
        """Récupère une information d'erreur par son code"""
        all_codes = cls.get_all_codes()
        return all_codes.get(code)
    
    @classmethod
    def get_by_category(cls, category: str) -> Dict[str, ErrorInfo]:
        """Récupère toutes les erreurs d'une catégorie"""
        all_codes = cls.get_all_codes()
        return {code: info for code, info in all_codes.items() if info.category == category}
