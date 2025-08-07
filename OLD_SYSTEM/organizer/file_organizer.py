import os
import shutil
import logging
from pathlib import Path
from config.config_manager import ConfigManager
from backup import record_file_organization

class FileOrganizer:
    def __init__(self, config, logger=None):
        self.config = config if isinstance(config, dict) else {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration par défaut
        self.base_output_dir = self.config.get('output_directory', './organized_music')
        self.create_year_folders = self.config.get('create_year_folders', True)
        self.pattern = self.config.get('naming_pattern', '{artist}/{album}/{track:02d} - {title}')
        self.dry_run = self.config.get('dry_run', False)
        
        # Créer le répertoire de sortie s'il n'existe pas
        if not self.dry_run:
            os.makedirs(self.base_output_dir, exist_ok=True)
    
    def organize_file(self, file_path, metadata):
        """Organise un fichier selon les métadonnées"""
        try:
            # Construire le chemin de destination
            destination_path = self._build_destination_path(file_path, metadata)
            
            if self.dry_run:
                self.logger.info(f"Dry run: {file_path} -> {destination_path}")
                return {
                    'status': 'dry_run',
                    'source': file_path,
                    'destination': destination_path,
                    'metadata': metadata
                }
            
            # Créer les répertoires nécessaires
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Copier ou déplacer le fichier
            if self.config.get('move_files', False):
                shutil.move(file_path, destination_path)
                action = "Déplacé"
            else:
                shutil.copy2(file_path, destination_path)
                action = "Copié"
            
            self.logger.info(f"{action}: {file_path} -> {destination_path}")
            
            # Enregistrer l'opération dans la base de données de backup
            try:
                record_file_organization(file_path, destination_path, metadata)
            except Exception as e:
                self.logger.warning(f"Impossible d'enregistrer l'opération dans le backup: {e}")
            
            return {
                'status': 'success',
                'source': file_path,
                'destination': destination_path,
                'action': action.lower(),
                'metadata': metadata
            }
            
        except Exception as e:
            error_msg = f"Erreur lors de l'organisation de {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return {
                'status': 'error',
                'source': file_path,
                'error': str(e),
                'metadata': metadata
            }
    
    def _build_destination_path(self, file_path, metadata):
        """Construit le chemin de destination basé sur les métadonnées"""
        # Obtenir l'extension du fichier original
        file_extension = Path(file_path).suffix
        
        # Préparer les variables pour le format
        format_vars = {
            'artist': self._sanitize_path(metadata.get('artist', 'Artiste Inconnu')),
            'album': self._sanitize_path(metadata.get('album', 'Album Inconnu')),
            'title': self._sanitize_path(metadata.get('title', 'Titre Inconnu')),
            'year': metadata.get('year', ''),
            'track': self._safe_int(metadata.get('track_number', 0)),
            'genre': self._sanitize_path(metadata.get('genre', '')),
        }
        
        # Construire le chemin selon le pattern
        try:
            relative_path = self.pattern.format(**format_vars)
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Erreur de formatage du pattern: {e}. Utilisation du pattern par défaut.")
            relative_path = f"{format_vars['artist']}/{format_vars['album']}/{format_vars['title']}"
        
        # Ajouter l'année si demandé
        if self.create_year_folders and format_vars['year']:
            year = self._extract_year(format_vars['year'])
            if year:
                relative_path = f"{year}/{relative_path}"
        
        # Construire le chemin complet
        full_path = os.path.join(self.base_output_dir, relative_path + file_extension)
        
        # Gérer les doublons
        return self._handle_duplicates(full_path)
    
    def _sanitize_path(self, path_component):
        """Nettoie un composant de chemin pour le système de fichiers"""
        if not path_component:
            return "Inconnu"
        
        # Remplacer les caractères interdits
        sanitized = path_component.replace('/', '_').replace('\\', '_')
        sanitized = sanitized.replace(':', '_').replace('*', '_')
        sanitized = sanitized.replace('?', '_').replace('"', '_')
        sanitized = sanitized.replace('<', '_').replace('>', '_')
        sanitized = sanitized.replace('|', '_')
        
        # Supprimer les espaces en début/fin
        sanitized = sanitized.strip()
        
        # Limiter la longueur
        return sanitized[:100] if len(sanitized) > 100 else sanitized
    
    def _safe_int(self, value):
        """Convertit une valeur en entier de manière sécurisée"""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def _extract_year(self, date_string):
        """Extrait l'année d'une chaîne de date"""
        if not date_string:
            return None
        
        # Essayer de trouver une année (4 chiffres)
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', str(date_string))
        return year_match.group() if year_match else None
    
    def _handle_duplicates(self, file_path):
        """Gère les fichiers en double en ajoutant un suffixe"""
        if not os.path.exists(file_path):
            return file_path
        
        base, ext = os.path.splitext(file_path)
        counter = 1
        
        while os.path.exists(f"{base} ({counter}){ext}"):
            counter += 1
        
        return f"{base} ({counter}){ext}"
    
    def get_stats(self):
        """Retourne des statistiques sur l'organisation"""
        if not os.path.exists(self.base_output_dir):
            return {'total_files': 0, 'total_folders': 0}
        
        total_files = 0
        total_folders = 0
        
        for root, dirs, files in os.walk(self.base_output_dir):
            total_folders += len(dirs)
            total_files += len(files)
        
        return {
            'total_files': total_files,
            'total_folders': total_folders,
            'base_directory': self.base_output_dir
        }
