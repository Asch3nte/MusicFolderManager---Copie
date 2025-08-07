#!/usr/bin/env python3
"""
Script de nettoyage des fichiers backup (.backup)
Supprime tous les fichiers .backup pour économiser l'espace disque
"""

import os
import sys
from pathlib import Path

def clean_backup_files(root_path):
    """Supprime tous les fichiers .backup dans un répertoire et ses sous-répertoires"""
    root_path = Path(root_path)
    backup_files = []
    total_size = 0
    
    print(f"🔍 Recherche des fichiers .backup dans {root_path}...")
    
    # Rechercher tous les fichiers .backup
    for backup_file in root_path.rglob("*.backup"):
        if backup_file.is_file():
            size = backup_file.stat().st_size
            backup_files.append((backup_file, size))
            total_size += size
    
    if not backup_files:
        print("✅ Aucun fichier .backup trouvé !")
        return
    
    print(f"📊 Trouvé {len(backup_files)} fichiers .backup")
    print(f"💾 Espace total utilisé: {total_size / (1024*1024):.1f} MB")
    print()
    
    # Demander confirmation
    response = input("⚠️ Voulez-vous supprimer tous ces fichiers .backup ? (o/N): ")
    if response.lower() not in ['o', 'oui', 'y', 'yes']:
        print("❌ Suppression annulée.")
        return
    
    # Supprimer les fichiers
    deleted_count = 0
    deleted_size = 0
    
    for backup_file, size in backup_files:
        try:
            backup_file.unlink()
            deleted_count += 1
            deleted_size += size
            print(f"✅ Supprimé: {backup_file}")
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de {backup_file}: {e}")
    
    print()
    print(f"🎉 Nettoyage terminé !")
    print(f"📁 Fichiers supprimés: {deleted_count}/{len(backup_files)}")
    print(f"💾 Espace libéré: {deleted_size / (1024*1024):.1f} MB")

def main():
    if len(sys.argv) != 2:
        print("Usage: python cleanup_backup_files.py <chemin_du_dossier>")
        print("Exemple: python cleanup_backup_files.py C:\\Music")
        sys.exit(1)
    
    root_path = sys.argv[1]
    
    if not os.path.exists(root_path):
        print(f"❌ Le chemin {root_path} n'existe pas !")
        sys.exit(1)
    
    clean_backup_files(root_path)

if __name__ == "__main__":
    main()
