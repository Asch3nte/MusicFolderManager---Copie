#!/usr/bin/env python3
"""
Détecteur de fichiers audio non-originaux
Compare durée réelle vs durée de référence pour identifier les versions modifiées
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

class NonOriginalDetector:
    """Détecteur de fichiers audio non-originaux"""
    
    def __init__(self, tolerance_seconds: float = 2.0):
        self.tolerance_seconds = tolerance_seconds
        self.suspicious_files = []
        self.analysis_results = {}
        
        # Extensions suspectes
        self.suspicious_extensions = [
            '.m4a',  # Souvent utilisé pour les downloads
            '.webm', '.3gp', '.amr'  # Formats de streaming
        ]
        
        # Bitrates suspects (trop bas ou artificiels)
        self.suspicious_bitrates = [
            64, 96, 112, 128,  # Très bas
            129, 192, 256,     # Souvent des re-encodages
        ]
    
    def analyze_duration_mismatch(self, 
                                actual_duration: float, 
                                reference_duration: float,
                                file_path: str,
                                metadata: Dict) -> Dict:
        """Analyse les différences de durée entre fichier et référence"""
        
        if not reference_duration or reference_duration <= 0:
            return {
                'status': 'no_reference',
                'suspicious': False,
                'reason': 'Pas de durée de référence disponible'
            }
        
        duration_diff = abs(actual_duration - reference_duration)
        duration_diff_percent = (duration_diff / reference_duration) * 100
        
        # Déterminer le niveau de suspicion
        if duration_diff <= self.tolerance_seconds:
            status = 'match'
            suspicious = False
            reason = f'Durée correspond (différence: {duration_diff:.1f}s)'
        elif duration_diff <= 5.0:
            status = 'minor_difference'
            suspicious = True
            reason = f'Petite différence de durée ({duration_diff:.1f}s, {duration_diff_percent:.1f}%)'
        elif duration_diff <= 15.0:
            status = 'moderate_difference'
            suspicious = True
            reason = f'Différence modérée de durée ({duration_diff:.1f}s, {duration_diff_percent:.1f}%)'
        else:
            status = 'major_difference'
            suspicious = True
            reason = f'Différence majeure de durée ({duration_diff:.1f}s, {duration_diff_percent:.1f}%)'
        
        return {
            'status': status,
            'suspicious': suspicious,
            'reason': reason,
            'actual_duration': actual_duration,
            'reference_duration': reference_duration,
            'duration_difference': duration_diff,
            'duration_difference_percent': duration_diff_percent
        }
    
    def analyze_filename_patterns(self, file_path: str) -> Dict:
        """Analyse des patterns de nom de fichier (désactivée)"""
        # Détection basée sur le nom de fichier désactivée
        return {
            'suspicious': False,
            'found_patterns': [],
            'reason': 'Analyse du nom de fichier désactivée'
        }
    
    def analyze_technical_properties(self, metadata: Dict) -> Dict:
        """Analyse les propriétés techniques suspectes"""
        suspicious_indicators = []
        
        # Vérifier le bitrate
        bitrate = metadata.get('bitrate', 0)
        if bitrate in self.suspicious_bitrates:
            suspicious_indicators.append(f'bitrate suspect ({bitrate} kbps)')
        
        # Vérifier l'extension
        file_format = metadata.get('format', '').lower()
        if any(ext in file_format for ext in self.suspicious_extensions):
            suspicious_indicators.append(f'format suspect ({file_format})')
        
        # Vérifier la sample rate
        sample_rate = metadata.get('sample_rate', 0)
        if sample_rate < 44100:
            suspicious_indicators.append(f'sample rate bas ({sample_rate} Hz)')
        
        # Vérifier les canaux
        channels = metadata.get('channels', 2)
        if channels == 1:
            suspicious_indicators.append('mono (possiblement dégradé)')
        
        suspicious = len(suspicious_indicators) > 0
        
        return {
            'suspicious': suspicious,
            'indicators': suspicious_indicators,
            'reason': f'Indicateurs techniques: {", ".join(suspicious_indicators)}' if suspicious_indicators else 'Propriétés techniques normales'
        }
    
    def analyze_metadata_inconsistencies(self, metadata: Dict) -> Dict:
        """Analyse les incohérences dans les métadonnées"""
        inconsistencies = []
        
        # Vérifier les champs manquants critiques
        if not metadata.get('musicbrainz_id'):
            inconsistencies.append('Pas d\'ID MusicBrainz')
        
        if not metadata.get('isrc'):
            inconsistencies.append('Pas d\'ISRC')
        
        # Vérifier la cohérence artiste/album_artist
        artist = metadata.get('artist', '')
        album_artist = metadata.get('album_artist', '')
        if artist and album_artist and artist != album_artist:
            # C'est normal pour les compilations, mais noter
            inconsistencies.append('Artiste différent de l\'artiste d\'album (compilation possible)')
        
        # Vérifier l'année
        year = metadata.get('year')
        if not year or year < 1900 or year > datetime.now().year:
            inconsistencies.append('Année manquante ou invalide')
        
        suspicious = len(inconsistencies) > 2  # Plus de 2 incohérences = suspect
        
        return {
            'suspicious': suspicious,
            'inconsistencies': inconsistencies,
            'reason': f'Incohérences métadonnées: {", ".join(inconsistencies)}' if inconsistencies else 'Métadonnées cohérentes'
        }
    
    def full_analysis(self, 
                     file_path: str,
                     actual_duration: float,
                     reference_duration: float,
                     metadata: Dict) -> Dict:
        """Analyse complète d'un fichier pour détecter s'il est non-original"""
        
        # Analyses individuelles
        duration_analysis = self.analyze_duration_mismatch(actual_duration, reference_duration, file_path, metadata)
        filename_analysis = self.analyze_filename_patterns(file_path)
        technical_analysis = self.analyze_technical_properties(metadata)
        metadata_analysis = self.analyze_metadata_inconsistencies(metadata)
        
        # Score de suspicion (0-100)
        suspicion_score = 0
        
        if duration_analysis['suspicious']:
            if duration_analysis['status'] == 'major_difference':
                suspicion_score += 40
            elif duration_analysis['status'] == 'moderate_difference':
                suspicion_score += 25
            else:
                suspicion_score += 15
        
        # Analyse du nom de fichier désactivée
        # if filename_analysis['suspicious']:
        #     suspicion_score += 20
        
        if technical_analysis['suspicious']:
            suspicion_score += len(technical_analysis['indicators']) * 5
        
        if metadata_analysis['suspicious']:
            suspicion_score += 15
        
        # Déterminer le verdict final
        if suspicion_score >= 50:
            verdict = 'highly_suspicious'
            verdict_text = 'Très probablement non-original'
        elif suspicion_score >= 30:
            verdict = 'suspicious'
            verdict_text = 'Probablement non-original'
        elif suspicion_score >= 15:
            verdict = 'questionable'
            verdict_text = 'Qualité douteuse'
        else:
            verdict = 'likely_original'
            verdict_text = 'Probablement original'
        
        # Générer un hash unique pour le fichier
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        
        analysis_result = {
            'file_path': file_path,
            'file_hash': file_hash,
            'analysis_timestamp': datetime.now().isoformat(),
            'verdict': verdict,
            'verdict_text': verdict_text,
            'suspicion_score': suspicion_score,
            'duration_analysis': duration_analysis,
            'filename_analysis': filename_analysis,
            'technical_analysis': technical_analysis,
            'metadata_analysis': metadata_analysis,
            'metadata_summary': {
                'title': metadata.get('title', 'N/A'),
                'artist': metadata.get('artist', 'N/A'),
                'album': metadata.get('album', 'N/A'),
                'bitrate': metadata.get('bitrate', 'N/A'),
                'format': metadata.get('format', 'N/A')
            }
        }
        
        # Stocker le résultat
        self.analysis_results[file_hash] = analysis_result
        
        # Ajouter à la liste des fichiers suspects si nécessaire
        if suspicion_score >= 15:
            self.suspicious_files.append(analysis_result)
        
        return analysis_result
    
    def generate_report(self, output_dir: str) -> Dict[str, str]:
        """Génère les rapports de détection"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport détaillé JSON
        json_report_path = output_dir / f"non_original_detection_{timestamp}.json"
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_summary': {
                    'total_files_analyzed': len(self.analysis_results),
                    'suspicious_files_count': len(self.suspicious_files),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'tolerance_seconds': self.tolerance_seconds
                },
                'suspicious_files': self.suspicious_files,
                'all_results': list(self.analysis_results.values())
            }, f, indent=2, ensure_ascii=False)
        
        # Rapport CSV pour analyse facile
        csv_report_path = output_dir / f"suspicious_files_{timestamp}.csv"
        with open(csv_report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Fichier', 'Verdict', 'Score Suspicion', 'Durée Réelle', 'Durée Référence',
                'Différence Durée', 'Titre', 'Artiste', 'Album', 'Bitrate', 'Format', 'Raisons'
            ])
            
            for result in self.suspicious_files:
                reasons = []
                if result['duration_analysis']['suspicious']:
                    reasons.append(result['duration_analysis']['reason'])
                # Analyse du nom de fichier désactivée
                # if result['filename_analysis']['suspicious']:
                #     reasons.append(result['filename_analysis']['reason'])
                if result['technical_analysis']['suspicious']:
                    reasons.append(result['technical_analysis']['reason'])
                if result['metadata_analysis']['suspicious']:
                    reasons.append(result['metadata_analysis']['reason'])
                
                writer.writerow([
                    result['file_path'],
                    result['verdict_text'],
                    result['suspicion_score'],
                    result['duration_analysis'].get('actual_duration', 'N/A'),
                    result['duration_analysis'].get('reference_duration', 'N/A'),
                    result['duration_analysis'].get('duration_difference', 'N/A'),
                    result['metadata_summary']['title'],
                    result['metadata_summary']['artist'],
                    result['metadata_summary']['album'],
                    result['metadata_summary']['bitrate'],
                    result['metadata_summary']['format'],
                    ' | '.join(reasons)
                ])
        
        # Rapport textuel lisible
        txt_report_path = output_dir / f"non_original_summary_{timestamp}.txt"
        with open(txt_report_path, 'w', encoding='utf-8') as f:
            f.write("🕵️ RAPPORT DE DÉTECTION DES FICHIERS NON-ORIGINAUX\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"📊 RÉSUMÉ:\n")
            f.write(f"   • Fichiers analysés: {len(self.analysis_results)}\n")
            f.write(f"   • Fichiers suspects: {len(self.suspicious_files)}\n")
            f.write(f"   • Tolérance durée: {self.tolerance_seconds}s\n")
            f.write(f"   • Date d'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.suspicious_files:
                f.write("🚨 FICHIERS SUSPECTS:\n")
                f.write("-" * 40 + "\n")
                
                for result in sorted(self.suspicious_files, key=lambda x: x['suspicion_score'], reverse=True):
                    f.write(f"\n📁 {Path(result['file_path']).name}\n")
                    f.write(f"   Verdict: {result['verdict_text']} (Score: {result['suspicion_score']})\n")
                    f.write(f"   Chemin: {result['file_path']}\n")
                    
                    if result['duration_analysis']['suspicious']:
                        f.write(f"   ⏱️ Durée: {result['duration_analysis']['reason']}\n")
                    
                    # Analyse du nom de fichier désactivée
                    # if result['filename_analysis']['suspicious']:
                    #     f.write(f"   📝 Nom: {result['filename_analysis']['reason']}\n")
                    
                    if result['technical_analysis']['suspicious']:
                        f.write(f"   🔧 Technique: {result['technical_analysis']['reason']}\n")
                    
                    if result['metadata_analysis']['suspicious']:
                        f.write(f"   📋 Métadonnées: {result['metadata_analysis']['reason']}\n")
            else:
                f.write("✅ Aucun fichier suspect détecté!\n")
        
        return {
            'json_report': str(json_report_path),
            'csv_report': str(csv_report_path),
            'txt_report': str(txt_report_path)
        }

def test_non_original_detector():
    """Test du détecteur de fichiers non-originaux"""
    detector = NonOriginalDetector(tolerance_seconds=2.0)
    
    # Test avec un fichier suspect
    test_metadata = {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'bitrate': 128,  # Suspect
        'format': 'mp3',
        'sample_rate': 22050,  # Bas
        'channels': 1  # Mono
    }
    
    result = detector.full_analysis(
        file_path="/path/to/youtube_rip_song.mp3",  # Nom suspect
        actual_duration=238.5,
        reference_duration=245.0,  # Différence de 6.5s
        metadata=test_metadata
    )
    
    print("🕵️ Test du détecteur de fichiers non-originaux")
    print("=" * 60)
    print(f"Verdict: {result['verdict_text']}")
    print(f"Score de suspicion: {result['suspicion_score']}/100")
    print(f"Analyse durée: {result['duration_analysis']['reason']}")
    print(f"Analyse nom: {result['filename_analysis']['reason']}")
    print(f"Analyse technique: {result['technical_analysis']['reason']}")

if __name__ == "__main__":
    test_non_original_detector()
