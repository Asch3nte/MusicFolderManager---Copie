#!/usr/bin/env python3
"""
Processeur de métadonnées amélioré pour MusicFolderManager
Intègre extraction complète + détection de fichiers non-originaux
"""

import sys
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple, Any

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from advanced_metadata_extractor import AdvancedMetadataExtractor
from non_original_detector import NonOriginalDetector
from intelligent_cache import IntelligentCache

class EnhancedMusicProcessor:
    """Processeur de musique avec extraction complète et détection d'authenticité"""
    
    def __init__(self, cache_enabled: bool = True):
        self.metadata_extractor = AdvancedMetadataExtractor()
        self.non_original_detector = NonOriginalDetector(tolerance_seconds=2.0)
        self.cache = IntelligentCache() if cache_enabled else None
        
        # Configuration du logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Statistiques de traitement
        self.stats = {
            'total_processed': 0,
            'metadata_enhanced': 0,
            'suspicious_files': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0
        }
    
    def get_file_audio_properties(self, file_path: str) -> Dict[str, Any]:
        """Extrait les propriétés audio du fichier"""
        try:
            # Utiliser l'analyseur spectral existant
            from spectral_analyzer import SpectralMatcher
            spectral_matcher = SpectralMatcher()
            
            features = spectral_matcher._extract_features(file_path)
            
            if features:
                return {
                    'duration': features.get('duration', 0),
                    'sample_rate': features.get('sample_rate', 0),
                    'format': features.get('format', ''),
                    'analysis_length': features.get('analysis_length', 0)
                }
            else:
                return {'duration': 0, 'sample_rate': 0, 'format': 'unknown'}
                
        except Exception as e:
            self.logger.error(f"Erreur extraction propriétés audio {file_path}: {e}")
            return {'duration': 0, 'sample_rate': 0, 'format': 'error'}
    
    def query_music_apis(self, file_path: str, fingerprint_data: Dict = None) -> Dict[str, Any]:
        """Interroge les APIs musicales pour récupérer les métadonnées complètes"""
        all_metadata = {}
        
        try:
            # Vérifier le cache d'abord
            if self.cache:
                cached_metadata = self.cache.get_cached_musicbrainz_response('enhanced_lookup', {'file_path': file_path})
                if cached_metadata:
                    self.stats['cache_hits'] += 1
                    return cached_metadata['data']
            
            # 1. Essayer avec AcousticID si on a un fingerprint
            if fingerprint_data and 'fingerprint' in fingerprint_data:
                try:
                    # Simuler une requête AcousticID (remplacer par vraie API)
                    acousticid_response = self._mock_acousticid_api(fingerprint_data)
                    if acousticid_response:
                        acousticid_metadata = self.metadata_extractor.extract_from_acousticid(acousticid_response)
                        all_metadata['acousticid'] = acousticid_metadata
                        self.stats['api_calls'] += 1
                except Exception as e:
                    self.logger.warning(f"Erreur AcousticID: {e}")
            
            # 2. Essayer avec MusicBrainz
            try:
                # Simuler une requête MusicBrainz (remplacer par vraie API)
                musicbrainz_response = self._mock_musicbrainz_api(file_path)
                if musicbrainz_response:
                    musicbrainz_metadata = self.metadata_extractor.extract_from_musicbrainz(musicbrainz_response)
                    all_metadata['musicbrainz'] = musicbrainz_metadata
                    self.stats['api_calls'] += 1
            except Exception as e:
                self.logger.warning(f"Erreur MusicBrainz: {e}")
            
            # 3. Essayer avec Last.fm
            try:
                # Simuler une requête Last.fm (remplacer par vraie API)
                lastfm_response = self._mock_lastfm_api(file_path)
                if lastfm_response:
                    lastfm_metadata = self.metadata_extractor.extract_from_lastfm(lastfm_response)
                    all_metadata['lastfm'] = lastfm_metadata
                    self.stats['api_calls'] += 1
            except Exception as e:
                self.logger.warning(f"Erreur Last.fm: {e}")
            
            # Fusionner toutes les métadonnées
            merged_metadata = self.metadata_extractor.merge_metadata(
                all_metadata.get('acousticid', {}),
                all_metadata.get('musicbrainz', {}),
                all_metadata.get('lastfm', {})
            )
            
            # Mettre en cache
            if self.cache and merged_metadata:
                self.cache.cache_musicbrainz_response('enhanced_lookup', {'file_path': file_path}, merged_metadata)
            
            return merged_metadata
            
        except Exception as e:
            self.logger.error(f"Erreur interrogation APIs: {e}")
            self.stats['errors'] += 1
            return {}
    
    def _mock_acousticid_api(self, fingerprint_data: Dict) -> Dict:
        """Mock de l'API AcousticID (remplacer par vraie API)"""
        # En production, faire la vraie requête AcousticID
        return {
            'results': [{
                'recordings': [{
                    'title': 'Example Song',
                    'length': int(fingerprint_data.get('duration', 0) * 1000),
                    'artist-credit': [{'artist': {'name': 'Example Artist'}}],
                    'releases': [{
                        'title': 'Example Album',
                        'date': '2023'
                    }]
                }]
            }]
        }
    
    def _mock_musicbrainz_api(self, file_path: str) -> Dict:
        """Mock de l'API MusicBrainz (remplacer par vraie API)"""
        # En production, faire la vraie requête MusicBrainz
        return {
            'recordings': [{
                'title': Path(file_path).stem,
                'length': 240000,
                'artist-credit': [{'artist': {'name': 'Mock Artist'}}],
                'releases': [{
                    'title': 'Mock Album',
                    'date': '2023-01-01'
                }]
            }]
        }
    
    def _mock_lastfm_api(self, file_path: str) -> Dict:
        """Mock de l'API Last.fm (remplacer par vraie API)"""
        # En production, faire la vraie requête Last.fm
        return {
            'track': {
                'name': Path(file_path).stem,
                'duration': 240000,
                'artist': {'name': 'Mock Artist'},
                'album': {'title': 'Mock Album'},
                'toptags': {
                    'tag': [
                        {'name': 'electronic'},
                        {'name': 'techno'},
                        {'name': 'dance'}
                    ]
                }
            }
        }
    
    def process_audio_file(self, file_path: str) -> Dict[str, Any]:
        """Traitement complet d'un fichier audio"""
        self.stats['total_processed'] += 1
        
        print(f"\n🎵 Traitement: {Path(file_path).name}")
        
        # 1. Extraire les propriétés audio du fichier
        print("   📊 Extraction propriétés audio...")
        audio_properties = self.get_file_audio_properties(file_path)
        
        # 2. Générer le fingerprint acoustique
        print("   🎧 Génération fingerprint...")
        fingerprint_data = None
        try:
            from fingerprint.acoustic_matcher import AcousticMatcher
            acoustic_matcher = AcousticMatcher()
            fingerprint_data = acoustic_matcher.generate_fingerprint(file_path)
        except Exception as e:
            self.logger.warning(f"Erreur fingerprint: {e}")
        
        # 3. Interroger les APIs pour récupérer les métadonnées complètes
        print("   🌐 Interrogation APIs musicales...")
        api_metadata = self.query_music_apis(file_path, fingerprint_data)
        
        # 4. Analyser l'authenticité du fichier
        print("   🕵️ Analyse authenticité...")
        reference_duration = api_metadata.get('duration', 0)
        actual_duration = audio_properties.get('duration', 0)
        
        # Combiner toutes les métadonnées
        combined_metadata = {**audio_properties, **api_metadata}
        
        authenticity_analysis = self.non_original_detector.full_analysis(
            file_path=file_path,
            actual_duration=actual_duration,
            reference_duration=reference_duration,
            metadata=combined_metadata
        )
        
        # 5. Valider la complétude des métadonnées
        completeness_report = self.metadata_extractor.validate_metadata_completeness(api_metadata)
        
        # 6. Mettre à jour les statistiques
        if api_metadata:
            self.stats['metadata_enhanced'] += 1
        
        if authenticity_analysis['suspicion_score'] >= 15:
            self.stats['suspicious_files'] += 1
        
        # 7. Préparer le résultat final
        result = {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'processing_success': True,
            'audio_properties': audio_properties,
            'fingerprint_data': fingerprint_data,
            'metadata': api_metadata,
            'authenticity_analysis': authenticity_analysis,
            'completeness_report': completeness_report,
            'recommendations': self._generate_recommendations(api_metadata, authenticity_analysis, completeness_report)
        }
        
        # Afficher le résumé
        self._print_processing_summary(result)
        
        return result
    
    def _generate_recommendations(self, metadata: Dict, authenticity: Dict, completeness: Dict) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Recommandations métadonnées
        if completeness['completeness_percentage'] < 70:
            recommendations.append("Métadonnées incomplètes - recherche manuelle recommandée")
        
        if not metadata.get('album_artist'):
            recommendations.append("Définir l'artiste d'album")
        
        if not metadata.get('year'):
            recommendations.append("Ajouter l'année de sortie")
        
        if not metadata.get('genre'):
            recommendations.append("Ajouter le genre musical")
        
        if not metadata.get('track_number'):
            recommendations.append("Définir le numéro de piste")
        
        # Recommandations authenticité
        if authenticity['verdict'] in ['highly_suspicious', 'suspicious']:
            recommendations.append("⚠️ Fichier possiblement non-original - vérification manuelle recommandée")
        
        if authenticity['verdict'] == 'questionable':
            recommendations.append("Qualité du fichier douteuse")
        
        # Recommandations techniques
        if metadata.get('sample_rate', 0) < 44100:
            recommendations.append("Sample rate bas - qualité limitée")
        
        if metadata.get('bitrate', 0) < 160:
            recommendations.append("Bitrate bas - compression élevée")
        
        return recommendations
    
    def _print_processing_summary(self, result: Dict) -> None:
        """Affiche un résumé du traitement"""
        metadata = result['metadata']
        authenticity = result['authenticity_analysis']
        completeness = result['completeness_report']
        
        print(f"   📋 Métadonnées:")
        print(f"      Titre: {metadata.get('title', 'N/A')}")
        print(f"      Artiste: {metadata.get('artist', 'N/A')}")
        print(f"      Album: {metadata.get('album', 'N/A')}")
        print(f"      Artiste album: {metadata.get('album_artist', 'N/A')}")
        print(f"      Année: {metadata.get('year', 'N/A')}")
        print(f"      Genre: {metadata.get('genre', 'N/A')}")
        print(f"      Piste: {metadata.get('track_number', 'N/A')}")
        
        print(f"   📊 Complétude: {completeness['completeness_percentage']:.1f}%")
        print(f"   🕵️ Authenticité: {authenticity['verdict_text']} (Score: {authenticity['suspicion_score']})")
        
        if result['recommendations']:
            print(f"   💡 Recommandations:")
            for rec in result['recommendations'][:3]:  # Top 3
                print(f"      • {rec}")
    
    def generate_processing_report(self, output_dir: str) -> Dict[str, str]:
        """Génère un rapport de traitement"""
        # Générer le rapport de détection de fichiers non-originaux
        non_original_reports = self.non_original_detector.generate_report(output_dir)
        
        # Créer un rapport de statistiques de traitement
        stats_report_path = Path(output_dir) / "processing_statistics.txt"
        with open(stats_report_path, 'w', encoding='utf-8') as f:
            f.write("📊 RAPPORT DE TRAITEMENT MUSICFOLDERMANAGER\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"📈 STATISTIQUES GÉNÉRALES:\n")
            f.write(f"   • Fichiers traités: {self.stats['total_processed']}\n")
            f.write(f"   • Métadonnées améliorées: {self.stats['metadata_enhanced']}\n")
            f.write(f"   • Fichiers suspects: {self.stats['suspicious_files']}\n")
            f.write(f"   • Utilisations du cache: {self.stats['cache_hits']}\n")
            f.write(f"   • Appels API: {self.stats['api_calls']}\n")
            f.write(f"   • Erreurs: {self.stats['errors']}\n\n")
            
            if self.stats['total_processed'] > 0:
                f.write(f"📊 RATIOS:\n")
                f.write(f"   • Taux d'amélioration métadonnées: {(self.stats['metadata_enhanced']/self.stats['total_processed']*100):.1f}%\n")
                f.write(f"   • Taux de fichiers suspects: {(self.stats['suspicious_files']/self.stats['total_processed']*100):.1f}%\n")
                f.write(f"   • Efficacité cache: {(self.stats['cache_hits']/(self.stats['cache_hits']+self.stats['api_calls'])*100):.1f}%\n")
        
        return {
            'processing_stats': str(stats_report_path),
            **non_original_reports
        }

def test_enhanced_processor():
    """Test du processeur amélioré"""
    processor = EnhancedMusicProcessor()
    
    # Test avec un fichier d'exemple
    test_file = "test_audio.mp3"
    
    print("🧪 Test du processeur de métadonnées amélioré")
    print("=" * 60)
    
    # Simuler le traitement
    result = processor.process_audio_file(test_file)
    
    print(f"\n📊 Résumé du test:")
    print(f"   Succès: {result['processing_success']}")
    print(f"   Recommandations: {len(result['recommendations'])}")
    
    # Générer un rapport
    reports = processor.generate_processing_report("test_output")
    print(f"\n📄 Rapports générés:")
    for report_type, path in reports.items():
        print(f"   {report_type}: {path}")

if __name__ == "__main__":
    test_enhanced_processor()
