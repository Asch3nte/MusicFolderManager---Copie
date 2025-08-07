import logging
import re

class MetadataManager:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.require_https = True  # Sécurité basique
        
    def consolidate_metadata(self, acoustid_data):
        """Structure sécurisée avec valeurs par défaut"""
        if not acoustid_data:
            return self._get_default_metadata()
            
        return {
            'artist': self._get_safe_field(acoustid_data, ['artists', 0, 'name'], 'Artiste Inconnu'),
            'title': self._get_safe_field(acoustid_data, ['title'], 'Titre Inconnu'),
            'album': self._get_safe_field(acoustid_data, ['release', 'title'], 'Album Inconnu'),
            'year': self._get_safe_field(acoustid_data, ['release', 'date'], ''),
            'genre': self._get_safe_field(acoustid_data, ['genre'], ''),
            'track_number': self._get_safe_field(acoustid_data, ['track'], ''),
            'duration': self._get_safe_field(acoustid_data, ['duration'], 0),
            'acoustid': self._get_safe_field(acoustid_data, ['id'], ''),
        }

    def _get_safe_field(self, data, path, default=''):
        """Accès sécurisé aux données imbriquées"""
        try:
            current = data
            for key in path:
                if isinstance(current, list) and isinstance(key, int):
                    current = current[key] if len(current) > key else None
                elif isinstance(current, dict):
                    current = current.get(key)
                else:
                    return default
                    
                if current is None:
                    return default
                    
            result = current if current else default
            return self.sanitize_filename(str(result)) if isinstance(result, str) else result
        except (KeyError, TypeError, IndexError, AttributeError):
            return default

    def sanitize_filename(self, name):
        """Nettoyage des noms de fichiers"""
        if not name:
            return ''
        # Supprime les caractères interdits dans les noms de fichiers Windows
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', str(name))
        # Supprime les espaces en début/fin
        cleaned = cleaned.strip()
        # Limite la longueur (facultatif)
        return cleaned[:100] if len(cleaned) > 100 else cleaned
    
    def _get_default_metadata(self):
        """Métadonnées par défaut quand aucune donnée AcoustID n'est disponible"""
        return {
            'artist': 'Artiste Inconnu',
            'title': 'Titre Inconnu',
            'album': 'Album Inconnu',
            'year': '',
            'genre': '',
            'track_number': '',
            'duration': 0,
            'acoustid': '',
        }
    
    def validate_metadata(self, metadata):
        """Valide et nettoie les métadonnées"""
        required_fields = ['artist', 'title', 'album']
        
        for field in required_fields:
            if not metadata.get(field) or metadata[field] in ['', 'Inconnu']:
                self.logger.warning(f"Champ requis manquant ou vide: {field}")
        
        # Nettoyage supplémentaire
        for key, value in metadata.items():
            if isinstance(value, str):
                metadata[key] = self.sanitize_filename(value)
        
        return metadata
