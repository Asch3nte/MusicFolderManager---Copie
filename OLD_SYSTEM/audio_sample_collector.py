#!/usr/bin/env python3
"""
Collecteur d'échantillons audio par extension
Parcourt une bibliothèque musicale et copie 1 fichier par extension trouvée
"""

import os
import shutil
import sys
from pathlib import Path
from collections import defaultdict
import time

class AudioSampleCollector:
    """Collecteur d'échantillons audio par extension"""
    
    def __init__(self):
        # Extensions audio reconnues (exhaustive)
        self.audio_extensions = {
            # Formats lossless
            '.wav', '.flac', '.aiff', '.aif', '.alac', '.ape', '.wv', '.dsd', '.dsf', '.dff',
            # Formats avec perte
            '.mp3', '.aac', '.m4a', '.ogg', '.oga', '.opus', '.wma', '.mka',
            # Formats professionnels
            '.ac3', '.dts', '.eac3', '.thd', '.truehd',
            # Formats rares/anciens
            '.ra', '.rm', '.amr', '.gsm', '.vox', '.au', '.snd', '.voc',
            # Formats module/tracker
            '.mod', '.it', '.xm', '.s3m', '.mtm', '.669', '.ult',
            # Formats propriétaires
            '.mpc', '.wv', '.tta', '.tak', '.ofr', '.als', '.shn'
        }
        
        self.found_extensions = set()
        self.samples_collected = {}
        self.stats = {
            'total_files_scanned': 0,
            'audio_files_found': 0,
            'extensions_found': 0,
            'samples_copied': 0,
            'scan_time': 0,
            'copy_time': 0
        }
    
    def is_audio_file(self, file_path):
        """Vérifie si un fichier est un fichier audio"""
        return file_path.suffix.lower() in self.audio_extensions
    
    def get_file_info(self, file_path):
        """Récupère des informations sur le fichier"""
        try:
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            return {
                'size_mb': round(size_mb, 2),
                'modified': time.ctime(stat.st_mtime)
            }
        except:
            return {'size_mb': 0, 'modified': 'Unknown'}
    
    def scan_library(self, library_path, max_depth=10):
        """Parcourt la bibliothèque à la recherche d'échantillons"""
        library_path = Path(library_path)
        
        if not library_path.exists():
            raise ValueError(f"Le chemin de bibliothèque n'existe pas: {library_path}")
        
        print(f"🔍 Scan de la bibliothèque: {library_path}")
        print(f"📁 Recherche de fichiers audio...")
        
        scan_start = time.time()
        
        # Parcours récursif avec limitation de profondeur
        for root, dirs, files in os.walk(library_path):
            # Limiter la profondeur
            current_depth = len(Path(root).relative_to(library_path).parts)
            if current_depth > max_depth:
                dirs.clear()  # Ne pas descendre plus profond
                continue
            
            for file in files:
                file_path = Path(root) / file
                self.stats['total_files_scanned'] += 1
                
                # Afficher le progrès tous les 1000 fichiers
                if self.stats['total_files_scanned'] % 1000 == 0:
                    print(f"   📊 {self.stats['total_files_scanned']} fichiers scannés, "
                          f"{len(self.found_extensions)} extensions trouvées...")
                
                if self.is_audio_file(file_path):
                    self.stats['audio_files_found'] += 1
                    extension = file_path.suffix.lower()
                    
                    # Si c'est une nouvelle extension, l'enregistrer
                    if extension not in self.found_extensions:
                        self.found_extensions.add(extension)
                        
                        # Récupérer infos du fichier
                        file_info = self.get_file_info(file_path)
                        
                        self.samples_collected[extension] = {
                            'path': file_path,
                            'size_mb': file_info['size_mb'],
                            'modified': file_info['modified'],
                            'name': file_path.name
                        }
                        
                        print(f"   🎵 Nouveau format trouvé: {extension.upper()} - {file_path.name}")
                        self.stats['extensions_found'] += 1
        
        self.stats['scan_time'] = time.time() - scan_start
        
        print(f"\n✅ Scan terminé en {self.stats['scan_time']:.2f}s")
        print(f"📊 Statistiques du scan:")
        print(f"   • Fichiers scannés: {self.stats['total_files_scanned']:,}")
        print(f"   • Fichiers audio trouvés: {self.stats['audio_files_found']:,}")
        print(f"   • Extensions différentes: {self.stats['extensions_found']}")
    
    def copy_samples(self, destination_path, preserve_structure=False):
        """Copie les échantillons vers le dossier de destination"""
        destination_path = Path(destination_path)
        destination_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Copie des échantillons vers: {destination_path}")
        
        copy_start = time.time()
        
        for extension, sample_info in self.samples_collected.items():
            source_path = sample_info['path']
            
            if preserve_structure:
                # Garder un peu de la structure (dernier dossier parent)
                parent_folder = source_path.parent.name
                dest_folder = destination_path / f"{extension[1:].upper()}_{parent_folder}"
                dest_folder.mkdir(exist_ok=True)
                dest_file = dest_folder / source_path.name
            else:
                # Copie directe avec préfixe d'extension
                dest_file = destination_path / f"{extension[1:].upper()}_{source_path.name}"
            
            try:
                print(f"   📋 Copie {extension.upper()}: {source_path.name} "
                      f"({sample_info['size_mb']}MB)")
                
                shutil.copy2(source_path, dest_file)
                self.stats['samples_copied'] += 1
                
            except Exception as e:
                print(f"   ❌ Erreur copie {extension.upper()}: {e}")
        
        self.stats['copy_time'] = time.time() - copy_start
        
        print(f"\n✅ Copie terminée en {self.stats['copy_time']:.2f}s")
        print(f"📦 {self.stats['samples_copied']} échantillons copiés")
    
    def generate_report(self, output_file=None):
        """Génère un rapport détaillé"""
        report_lines = [
            "🎵 RAPPORT DE COLLECTE D'ÉCHANTILLONS AUDIO",
            "=" * 60,
            "",
            f"📊 STATISTIQUES GÉNÉRALES:",
            f"   • Durée scan: {self.stats['scan_time']:.2f}s",
            f"   • Durée copie: {self.stats['copy_time']:.2f}s",
            f"   • Fichiers scannés: {self.stats['total_files_scanned']:,}",
            f"   • Fichiers audio: {self.stats['audio_files_found']:,}",
            f"   • Extensions trouvées: {self.stats['extensions_found']}",
            f"   • Échantillons copiés: {self.stats['samples_copied']}",
            "",
            f"🎼 ÉCHANTILLONS COLLECTÉS:"
        ]
        
        # Trier par extension
        sorted_samples = sorted(self.samples_collected.items())
        
        for extension, sample_info in sorted_samples:
            report_lines.extend([
                f"",
                f"   📀 {extension.upper()}:",
                f"      📁 Fichier: {sample_info['name']}",
                f"      💾 Taille: {sample_info['size_mb']}MB",
                f"      📅 Modifié: {sample_info['modified']}",
                f"      🗂️ Chemin: {sample_info['path']}"
            ])
        
        # Formats détectés vs supportés
        supported_formats = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif', '.m4a', '.wma', '.opus', '.ac3', '.ape'}
        found_supported = self.found_extensions.intersection(supported_formats)
        found_unsupported = self.found_extensions - supported_formats
        
        report_lines.extend([
            "",
            f"🔧 COMPATIBILITÉ AVEC MUSICFOLDERMANAGER:",
            f"   ✅ Formats supportés trouvés ({len(found_supported)}): {', '.join(sorted(found_supported))}",
            f"   ⚠️ Formats non supportés ({len(found_unsupported)}): {', '.join(sorted(found_unsupported)) if found_unsupported else 'Aucun'}",
            "",
            f"💡 RECOMMANDATIONS:",
            f"   • Tester tous les formats supportés avec le diagnostic",
            f"   • Vérifier la qualité des conversions ffmpeg",
            f"   • Considérer la conversion des formats non supportés"
        ])
        
        report_text = "\n".join(report_lines)
        
        # Afficher le rapport
        print("\n" + report_text)
        
        # Sauvegarder si demandé
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Rapport sauvegardé: {output_file}")
        
        return report_text

def main():
    """Point d'entrée principal"""
    print("🎵 COLLECTEUR D'ÉCHANTILLONS AUDIO")
    print("=" * 50)
    
    # Demander les chemins
    if len(sys.argv) >= 3:
        library_path = sys.argv[1]
        destination_path = sys.argv[2]
    else:
        library_path = input("📁 Chemin de la bibliothèque musicale: ").strip('"')
        destination_path = input("📦 Dossier de destination pour les échantillons: ").strip('"')
    
    if not library_path or not destination_path:
        print("❌ Chemins manquants")
        return
    
    # Options
    preserve_structure = input("🗂️ Préserver la structure par dossier parent? (o/N): ").lower().startswith('o')
    max_depth = int(input("📊 Profondeur maximale de scan (défaut 10): ") or "10")
    
    try:
        # Créer le collecteur
        collector = AudioSampleCollector()
        
        # Scanner la bibliothèque
        collector.scan_library(library_path, max_depth=max_depth)
        
        if not collector.samples_collected:
            print("⚠️ Aucun fichier audio trouvé!")
            return
        
        # Copier les échantillons
        collector.copy_samples(destination_path, preserve_structure=preserve_structure)
        
        # Générer le rapport
        report_file = Path(destination_path) / "collection_report.txt"
        collector.generate_report(str(report_file))
        
        print(f"\n🎉 Collection terminée avec succès!")
        print(f"📁 Échantillons dans: {destination_path}")
        print(f"📄 Rapport dans: {report_file}")
        print(f"\n🧪 Prochaine étape: Tester avec diagnostic_spectres.py")
        
    except Exception as e:
        print(f"💥 Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
