import sys
import argparse
import os
import logging
import json
from pathlib import Path

# Configuration du chemin vers fpcalc.exe
CURRENT_DIR = Path(__file__).parent
FPCALC_PATH = CURRENT_DIR / "audio_tools" / "fpcalc.exe"

# Définir la variable d'environnement pour pyacoustid
if FPCALC_PATH.exists():
    os.environ['FPCALC'] = str(FPCALC_PATH)
    print(f"🎵 fpcalc configuré pour main.py: {FPCALC_PATH}")

from fingerprint.processor import AudioFingerprinter
from utils.parallel_processor import process_files_parallel
from utils.file_utils import is_audio_file
from organizer.metadata_manager import MetadataManager
from organizer.file_organizer import FileOrganizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scan_directory(directory):
    audio_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_audio_file(file_path):
                audio_files.append(file_path)
    return audio_files

def main():
    parser = argparse.ArgumentParser(description="Gestionnaire de bibliothèque musicale")
    parser.add_argument('directory', help="Répertoire à scanner")
    parser.add_argument('--output', help="Fichier de sortie JSON", default="results.json")
    parser.add_argument('--api-key', help="Clé API AcoustID", default="votre_api_key")
    parser.add_argument('--organize', action='store_true', help="Organiser les fichiers")
    parser.add_argument('--dry-run', action='store_true', help="Mode simulation")
    args = parser.parse_args()
    
    logger.info(f"Démarrage du scan de {args.directory}")
    audio_files = scan_directory(args.directory)
    logger.info(f"{len(audio_files)} fichiers audio trouvés")
    
    # Configuration pour l'organisateur
    config = {
        'output_directory': './organized_music',
        'create_year_folders': True,
        'naming_pattern': '{artist}/{album}/{track:02d} - {title}',
        'move_files': False,  # Copier par défaut
        'dry_run': args.dry_run
    }
    
    # Initialisation des composants
    metadata_manager = MetadataManager(logger=logger)
    organizer = FileOrganizer(config, logger=logger)
    fingerprinter = AudioFingerprinter(args.api_key, logger=logger)
    
    results = []
    
    logger.info("Début du traitement des fichiers...")
    
    for i, file_path in enumerate(audio_files, 1):
        logger.info(f"Traitement {i}/{len(audio_files)}: {file_path}")
        
        try:
            # 1. Acquisition fingerprint
            duration, fp = fingerprinter.get_fingerprint(file_path)
            
            # 2. Requête AcoustID
            acoustid_data = fingerprinter.query_acoustid(fp, duration)
            
            # 3. Extraction métadonnées
            metadata = metadata_manager.consolidate_metadata(acoustid_data)
            metadata = metadata_manager.validate_metadata(metadata)
            
            # 4. Réorganisation du fichier (si demandé)
            organization_result = None
            if args.organize:
                organization_result = organizer.organize_file(file_path, metadata)
            
            # Enregistrer les résultats
            result = {
                'file_path': file_path,
                'duration': duration,
                'metadata': metadata,
                'acoustid_results_count': len(acoustid_data) if acoustid_data else 0,
                'status': 'success'
            }
            
            if organization_result:
                result['organization'] = organization_result
            
            results.append(result)
            
        except Exception as e:
            error_msg = f"Erreur lors du traitement de {file_path}: {str(e)}"
            logger.error(error_msg)
            results.append({
                'file_path': file_path,
                'status': 'error',
                'error': str(e)
            })
    
    # Sauvegarde des résultats
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Résultats enregistrés dans {args.output}")
    
    # Statistiques finales
    successful = len([r for r in results if r.get('status') == 'success'])
    failed = len([r for r in results if r.get('status') == 'error'])
    
    logger.info(f"Traitement terminé: {successful} réussis, {failed} échecs")
    
    if args.organize:
        stats = organizer.get_stats() if hasattr(organizer, 'get_stats') else {}
        logger.info(f"Statistiques d'organisation: {stats}")

if __name__ == "__main__":
    main()
