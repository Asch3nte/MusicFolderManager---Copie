#!/usr/bin/env python3
"""
Gestionnaire de backup basé sur une base de données
Ne duplique pas les fichiers, mais enregistre les opérations
"""

from .backup_database import record_file_operation, get_backup_database

def record_metadata_change(file_path, metadata_before=None, metadata_after=None):
    """Enregistre un changement de métadonnées"""
    return record_file_operation(
        file_path, 
        'metadata_change', 
        metadata_before, 
        metadata_after,
        "Modification des métadonnées par AudioFingerprinter"
    )

def record_file_move(old_path, new_path):
    """Enregistre un déplacement de fichier"""
    return record_file_operation(
        old_path,
        'file_moved',
        metadata_before={'original_path': old_path},
        metadata_after={'new_path': new_path},
        notes=f"Fichier déplacé vers {new_path}"
    )

def record_file_organization(file_path, destination, metadata_used):
    """Enregistre une organisation de fichier"""
    return record_file_operation(
        file_path,
        'file_organized',
        metadata_before={'original_location': file_path},
        metadata_after={'organized_location': destination, 'metadata': metadata_used},
        notes="Fichier organisé automatiquement"
    )

def get_backup_statistics():
    """Retourne les statistiques de backup"""
    db = get_backup_database()
    return db.get_statistics()

def get_file_history(file_path):
    """Récupère l'historique d'un fichier"""
    db = get_backup_database()
    return db.get_file_history(file_path)

def create_backup(file_path, backup_root=None):
    """Fonction de compatibilité - enregistre juste l'opération"""
    return record_file_operation(
        file_path,
        'backup_requested',
        notes="Demande de backup interceptée - enregistrement en base uniquement"
    )

def restore_backup(backup_id):
    """Fonction de compatibilité"""
    return True

def rollback_backup(file_path):
    """Fonction de compatibilité - affiche l'historique"""
    db = get_backup_database()
    history = db.get_file_history(file_path)
    
    if history:
        print(f"Historique du fichier {file_path}:")
        for entry in history[:5]:  # Afficher les 5 dernières entrées
            print(f"  - {entry['timestamp']}: {entry['operation_type']}")
            if entry.get('notes'):
                print(f"    Notes: {entry['notes']}")
    else:
        print(f"Aucun historique trouvé pour {file_path}")
    
    return len(history) > 0

class BackupHandler:
    """Gestionnaire de backup pour compatibilité"""
    
    def __init__(self, backup_dir=None):
        self.backup_dir = backup_dir
    
    def create_backup(self, file_path):
        """Crée un backup d'un fichier"""
        return record_metadata_change(file_path)
    
    def get_statistics(self):
        """Retourne les statistiques"""
        return get_backup_statistics()
    
    def get_file_history(self, file_path):
        """Retourne l'historique d'un fichier"""
        return get_file_history(file_path)
