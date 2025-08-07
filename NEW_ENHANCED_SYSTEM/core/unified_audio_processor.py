#!/usr/bin/env python3
"""
Processeur Audio Unifié - MusicFolderManager
Combine AcoustID, MusicBrainz, Analyse Spectrale et Extraction de Métadonnées
"""

import os
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json

# Imports pour l'analyse audio
from acoustid import fingerprint_file, lookup, parse_lookup_result

# Imports locaux
from cache.cache_manager import CacheManager
from config.enhanced_config_manager import EnhancedConfigManager
from errors import ErrorManager, get_error_manager, AudioProcessingError

class AnalysisMethod(Enum):
    """Méthodes d'analyse disponibles"""
    ACOUSTICID = "acousticid"
    SPECTRAL = "spectral"
    MUSICBRAINZ = "musicbrainz"
    METADATA_EXTRACTION = "metadata_extraction"

class AnalysisStatus(Enum):
    """Status du résultat d'analyse"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"
    CACHED = "cached"

@dataclass
class AnalysisResult:
    """Résultat unifié d'analyse audio"""
    status: AnalysisStatus
    file_path: str
    confidence: float = 0.0
    method_used: Optional[AnalysisMethod] = None
    
    # Métadonnées extraites
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Données techniques
    audio_properties: Dict[str, Any] = field(default_factory=dict)
    fingerprint_data: Optional[Dict[str, Any]] = None
    spectral_features: Optional[Dict[str, Any]] = None
    
    # Informations de processus
    processing_time: float = 0.0
    cache_hit: bool = False
    methods_attempted: List[AnalysisMethod] = field(default_factory=list)
    
    # Erreurs et suggestions pour révision manuelle
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    manual_review_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour sérialisation"""
        return {
            'status': self.status.value,
            'file_path': self.file_path,
            'confidence': self.confidence,
            'method_used': self.method_used.value if self.method_used else None,
            'metadata': self.metadata,
            'audio_properties': self.audio_properties,
            'fingerprint_data': self.fingerprint_data,
            'spectral_features': self.spectral_features,
            'processing_time': self.processing_time,
            'cache_hit': self.cache_hit,
            'methods_attempted': [m.value for m in self.methods_attempted],
            'errors': self.errors,
            'suggestions': self.suggestions,
            'manual_review_reason': self.manual_review_reason
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Création depuis un dictionnaire"""
        return cls(
            status=AnalysisStatus(data['status']),
            file_path=data['file_path'],
            confidence=data.get('confidence', 0.0),
            method_used=AnalysisMethod(data['method_used']) if data.get('method_used') else None,
            metadata=data.get('metadata', {}),
            audio_properties=data.get('audio_properties', {}),
            fingerprint_data=data.get('fingerprint_data'),
            spectral_features=data.get('spectral_features'),
            processing_time=data.get('processing_time', 0.0),
            cache_hit=data.get('cache_hit', False),
            methods_attempted=[AnalysisMethod(m) for m in data.get('methods_attempted', [])],
            errors=data.get('errors', []),
            suggestions=data.get('suggestions', []),
            manual_review_reason=data.get('manual_review_reason')
        )

class UnifiedAudioProcessor:
    """
    Processeur Audio Unifié
    
    Combine toutes les méthodes d'analyse en une seule classe cohérente :
    - AcoustID fingerprinting
    - Analyse spectrale 
    - Recherche MusicBrainz
    - Extraction de métadonnées
    """
    
    def __init__(self, api_key: str = None, config_path: str = None):
        """
        Initialise le processeur unifié
        
        Args:
            api_key: Clé API AcoustID (optionnelle si dans config)
            config_path: Chemin vers le fichier de configuration (ignoré pour compatibilité)
        """
        # Configuration
        self.config = EnhancedConfigManager.get_instance()
        self.cache = CacheManager.get_instance()
        self.error_manager = get_error_manager()
        self.logger = logging.getLogger(__name__)
        
        # API Key
        try:
            self.api_key = api_key or self.config.get('APIS', 'acoustid_api_key')
        except:
            self.api_key = api_key or ''
        
        # Configuration des seuils
        self.thresholds = {
            'acousticid_min_confidence': self._get_config_float('FINGERPRINT', 'acoustid_min_confidence', 0.85),
            'spectral_similarity_threshold': self._get_config_float('FINGERPRINT', 'spectral_similarity_threshold', 0.7),
            'musicbrainz_min_confidence': self._get_config_float('FINGERPRINT', 'musicbrainz_min_confidence', 0.7)
        }
        
        # Statistiques de session
        self.stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'acousticid_successes': 0,
            'spectral_successes': 0,
            'musicbrainz_successes': 0,
            'manual_reviews': 0,
            'errors': 0,
            'processing_time': 0.0
        }
        
        # Initialiser les composants spécialisés
        self._init_components()
        
        self.logger.info("🎵 Processeur Audio Unifié initialisé")
        self.logger.info("🎯 Ordre d'analyse: 1️⃣ AcoustID → 2️⃣ Spectral → 3️⃣ MusicBrainz")
        
        # Sécuriser l'affichage des seuils
        spectral_val = self.thresholds['spectral_similarity_threshold'] or 0.7
        acousticid_val = self.thresholds['acousticid_min_confidence'] or 0.85
        musicbrainz_val = self.thresholds['musicbrainz_min_confidence'] or 0.7
        
        self.logger.info(f"   📊 Seuils: Spectral={spectral_val:.2f}, "
                        f"AcoustID={acousticid_val:.2f}, "
                        f"MusicBrainz={musicbrainz_val:.2f}")
    
    def _get_config_float(self, section: str, key: str, default: float) -> float:
        """Récupère une valeur float de la configuration avec fallback"""
        try:
            value = self.config.getfloat(section, key, fallback=default)
            return value if value is not None else default
        except:
            return default
    
    def _init_components(self):
        """Initialise les composants spécialisés de manière paresseuse"""
        self._fingerprint_component = None
        self._spectral_component = None
        self._musicbrainz_component = None
        self._metadata_component = None
        
        # Configuration du chemin fpcalc
        current_dir = Path(__file__).parent
        self.fpcalc_path = current_dir / "audio_tools" / "fpcalc.exe"
        if self.fpcalc_path.exists():
            os.environ['FPCALC'] = str(self.fpcalc_path)
    
    @property
    def fingerprint_component(self):
        """Composant de fingerprinting (lazy loading)"""
        if self._fingerprint_component is None:
            from fingerprint.acoustic_matcher import AcousticMatcher
            self._fingerprint_component = AcousticMatcher(fpcalc_path=self.fpcalc_path)
        return self._fingerprint_component
    
    @property 
    def spectral_component(self):
        """Composant d'analyse spectrale (lazy loading)"""
        if self._spectral_component is None:
            from spectral_analyzer import SpectralMatcher
            self._spectral_component = SpectralMatcher(
                threshold=self.thresholds['spectral_similarity_threshold']
            )
        return self._spectral_component
    
    @property
    def musicbrainz_component(self):
        """Composant MusicBrainz (lazy loading)"""
        if self._musicbrainz_component is None:
            from fingerprint.musicbrainz_search import MusicBrainzSearcher
            self._musicbrainz_component = MusicBrainzSearcher(logger=self.logger)
        return self._musicbrainz_component
    
    @property
    def metadata_component(self):
        """Composant d'extraction de métadonnées (lazy loading)"""
        if self._metadata_component is None:
            from advanced_metadata_extractor import AdvancedMetadataExtractor
            self._metadata_component = AdvancedMetadataExtractor()
        return self._metadata_component
    
    def process_file(self, file_path: str, methods: List[AnalysisMethod] = None) -> AnalysisResult:
        """
        Traite un fichier audio avec toutes les méthodes disponibles
        
        Args:
            file_path: Chemin vers le fichier à analyser
            methods: Liste des méthodes à utiliser (None = toutes dans l'ordre optimal)
            
        Returns:
            AnalysisResult: Résultat complet de l'analyse
        """
        start_time = time.time()
        self.stats['total_processed'] += 1
        
        # Créer le résultat de base
        result = AnalysisResult(
            status=AnalysisStatus.FAILED,
            file_path=file_path
        )
        
        try:
            self.logger.info(f"🎵 Traitement: {Path(file_path).name}")
            
            # Vérifier le cache global d'abord
            cache_key = self._generate_cache_key(file_path)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                self.logger.info("💾 Résultat trouvé en cache")
                return cached_result
            
            # Définir l'ordre optimal des méthodes si non spécifié
            if methods is None:
                methods = [
                    AnalysisMethod.ACOUSTICID,      # 1. AcoustID (empreinte acoustique)
                    AnalysisMethod.SPECTRAL,        # 2. Analyse spectrale (caractéristiques sonores)
                    AnalysisMethod.MUSICBRAINZ,     # 3. MusicBrainz (recherche textuelle)
                    AnalysisMethod.METADATA_EXTRACTION  # 4. Extraction métadonnées (dernière chance)
                ]
            
            # Extraire les propriétés audio de base
            result.audio_properties = self._extract_audio_properties(file_path)
            
            # Essayer chaque méthode dans l'ordre jusqu'à succès
            for method in methods:
                try:
                    result.methods_attempted.append(method)
                    self.logger.info(f"   🔍 Tentative {method.value}...")
                    
                    method_result = self._apply_method(file_path, method, result)
                    
                    # Obtenir le seuil pour cette méthode
                    threshold_key = f'{method.value}_min_confidence'
                    if method.value == 'acousticid':
                        threshold_key = 'acousticid_min_confidence'
                    elif method.value == 'spectral':
                        threshold_key = 'spectral_similarity_threshold'
                    elif method.value == 'musicbrainz':
                        threshold_key = 'musicbrainz_min_confidence'
                    
                    threshold = self.thresholds.get(threshold_key, 0.7)
                    
                    if method_result and method_result.confidence >= threshold:
                        # Succès avec cette méthode
                        result.status = AnalysisStatus.SUCCESS
                        result.method_used = method
                        result.confidence = method_result.confidence
                        result.metadata.update(method_result.metadata)
                        
                        # Données spécifiques selon la méthode
                        if method == AnalysisMethod.ACOUSTICID:
                            result.fingerprint_data = method_result.fingerprint_data
                            self.stats['acousticid_successes'] += 1
                        elif method == AnalysisMethod.SPECTRAL:
                            result.spectral_features = method_result.spectral_features
                            self.stats['spectral_successes'] += 1
                        elif method == AnalysisMethod.MUSICBRAINZ:
                            self.stats['musicbrainz_successes'] += 1
                        
                        self.logger.info(f"✅ Succès avec {method.value} (confiance: {result.confidence:.2f})")
                        break
                        
                    else:
                        # Méthode échouée ou confiance insuffisante
                        if method_result:
                            self.logger.info(f"⚠️ {method.value} confiance trop faible: {method_result.confidence:.2f}")
                            # Garder les suggestions même si confiance faible
                            if method_result.metadata:
                                result.suggestions.extend([
                                    f"{method.value}: {method_result.metadata.get('artist', 'Inconnu')} - {method_result.metadata.get('title', 'Inconnu')} (confiance: {method_result.confidence:.2f})"
                                ])
                        
                except Exception as e:
                    error_msg = f"Erreur {method.value}: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.warning(error_msg)
                    self.stats['errors'] += 1
            
            # Si aucune méthode n'a réussi
            if result.status == AnalysisStatus.FAILED:
                result.status = AnalysisStatus.MANUAL_REVIEW
                result.manual_review_reason = self._analyze_failure_reason(result)
                self.stats['manual_reviews'] += 1
                self.logger.warning(f"❌ Révision manuelle requise: {result.manual_review_reason}")
            
            # Finaliser le résultat
            result.processing_time = time.time() - start_time
            self.stats['processing_time'] += result.processing_time
            
            # Mettre en cache si succès
            if result.status == AnalysisStatus.SUCCESS:
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            result.errors.append(f"Erreur critique: {str(e)}")
            result.processing_time = time.time() - start_time
            self.logger.error(f"💥 Erreur critique lors du traitement: {e}")
            return result
    
    def _apply_method(self, file_path: str, method: AnalysisMethod, base_result: AnalysisResult) -> Optional[AnalysisResult]:
        """Applique une méthode d'analyse spécifique"""
        
        if method == AnalysisMethod.ACOUSTICID:
            return self._apply_acousticid(file_path)
        elif method == AnalysisMethod.SPECTRAL:
            return self._apply_spectral_analysis(file_path)
        elif method == AnalysisMethod.MUSICBRAINZ:
            return self._apply_musicbrainz_search(file_path, base_result)
        elif method == AnalysisMethod.METADATA_EXTRACTION:
            return self._apply_metadata_extraction(file_path)
        
        return None
    
    def _apply_acousticid(self, file_path: str) -> Optional[AnalysisResult]:
        """Analyse par empreinte acoustique AcoustID"""
        try:
            # Générer le fingerprint
            fingerprint_data = self.fingerprint_component.generate_fingerprint(file_path)
            if not fingerprint_data or 'fingerprint' not in fingerprint_data:
                return None
            
            # Requête AcoustID
            results = lookup(
                apikey=self.api_key,
                fingerprint=fingerprint_data['fingerprint'], 
                duration=fingerprint_data['duration']
            )
            
            if not results.get('results'):
                return None
            
            # Meilleur match
            best_match = max(results['results'], key=lambda x: x['score'])
            recordings = best_match.get('recordings', [])
            
            if not recordings:
                return None
            
            recording = recordings[0]
            
            # Extraire métadonnées
            metadata = {
                'title': recording.get('title', ''),
                'duration': recording.get('length', 0) / 1000.0 if recording.get('length') else 0,
                'musicbrainz_id': recording.get('id', '')
            }
            
            # Artistes
            if 'artist-credit' in recording:
                artists = []
                for credit in recording['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                metadata['artist'] = ', '.join(filter(None, artists))
            
            # Albums
            if 'releases' in recording and recording['releases']:
                release = recording['releases'][0]
                metadata['album'] = release.get('title', '')
                metadata['year'] = release.get('date', '')[:4] if release.get('date') else ''
            
            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                file_path=file_path,
                confidence=best_match['score'],
                method_used=AnalysisMethod.ACOUSTICID,
                metadata=metadata,
                fingerprint_data=fingerprint_data
            )
            
        except Exception as e:
            self.logger.debug(f"AcoustID failed: {e}")
            return None
    
    def _apply_spectral_analysis(self, file_path: str) -> Optional[AnalysisResult]:
        """Analyse spectrale du fichier"""
        try:
            # Extraire les caractéristiques spectrales
            features = self.spectral_component._extract_features(file_path)
            if not features:
                return None
            
            # Pour l'instant, pas de base de données de référence pour le matching
            # Donc on retourne les caractéristiques avec une confiance faible
            # mais on peut améliorer en analysant les caractéristiques
            
            # Calculer une "confiance" basée sur la qualité des features
            confidence = 0.1  # Confiance de base faible
            
            # Augmenter la confiance si on a des données exploitables
            if features.get('duration', 0) > 30:  # Au moins 30 secondes
                confidence += 0.1
            if features.get('sample_rate', 0) >= 44100:  # Qualité CD ou mieux
                confidence += 0.1
            if features.get('spectral_centroid_mean', 0) > 0:  # Features spectrales valides
                confidence += 0.1
            
            return AnalysisResult(
                status=AnalysisStatus.PARTIAL_SUCCESS,
                file_path=file_path,
                confidence=confidence,
                method_used=AnalysisMethod.SPECTRAL,
                metadata={
                    'duration': features.get('duration', 0),
                    'format': features.get('format', ''),
                    'sample_rate': features.get('sample_rate', 0),
                    'spectral_quality': 'basic'
                },
                spectral_features=features
            )
            
        except Exception as e:
            self.logger.debug(f"Spectral analysis failed: {e}")
            return None
    
    def _apply_musicbrainz_search(self, file_path: str, base_result: AnalysisResult) -> Optional[AnalysisResult]:
        """Recherche MusicBrainz par métadonnées ou nom de fichier"""
        try:
            # Essayer d'abord avec les métadonnées existantes
            existing_metadata = self._extract_existing_metadata(file_path)
            musicbrainz_data = None
            
            if existing_metadata:
                musicbrainz_data = self.musicbrainz_component.search_by_metadata(existing_metadata)
            
            # Sinon essayer par nom de fichier
            if not musicbrainz_data:
                musicbrainz_data = self.musicbrainz_component.search_by_filename(file_path)
            
            if not musicbrainz_data or not musicbrainz_data.get('best_match'):
                return None
            
            best_match = musicbrainz_data['best_match']
            confidence = best_match.get('confidence', 0)
            
            # Formater les métadonnées
            formatted_metadata = self.musicbrainz_component.format_result(best_match)
            
            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                file_path=file_path,
                confidence=confidence,
                method_used=AnalysisMethod.MUSICBRAINZ,
                metadata=formatted_metadata
            )
            
        except Exception as e:
            self.logger.debug(f"MusicBrainz search failed: {e}")
            return None
    
    def _apply_metadata_extraction(self, file_path: str) -> Optional[AnalysisResult]:
        """Extraction de métadonnées depuis les tags du fichier"""
        try:
            metadata = self._extract_existing_metadata(file_path)
            if not metadata:
                return None
            
            # Vérifier qu'on a au minimum titre + artiste
            if not (metadata.get('title') and metadata.get('artist')):
                return None
            
            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                file_path=file_path,
                confidence=0.9,  # Haute confiance car données existantes
                method_used=AnalysisMethod.METADATA_EXTRACTION,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.debug(f"Metadata extraction failed: {e}")
            return None
    
    def _extract_audio_properties(self, file_path: str) -> Dict[str, Any]:
        """Extrait les propriétés audio de base"""
        try:
            features = self.spectral_component._extract_features(file_path)
            if features:
                return {
                    'duration': features.get('duration', 0),
                    'sample_rate': features.get('sample_rate', 0),
                    'format': features.get('format', ''),
                    'file_size': os.path.getsize(file_path)
                }
        except Exception as e:
            self.logger.debug(f"Audio properties extraction failed: {e}")
        
        return {'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0}
    
    def _extract_existing_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extrait les métadonnées existantes du fichier avec mutagen"""
        try:
            from mutagen import File
            
            audio_file = File(file_path)
            if not audio_file:
                return None
            
            metadata = {}
            
            # Extraction selon le format de fichier
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.mp3':
                # MP3 avec ID3
                metadata['title'] = self._get_tag_value(audio_file, 'TIT2')
                metadata['artist'] = self._get_tag_value(audio_file, 'TPE1')
                metadata['album'] = self._get_tag_value(audio_file, 'TALB')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'TPE2')
                metadata['date'] = self._get_tag_value(audio_file, 'TDRC')
                metadata['track'] = self._get_tag_value(audio_file, 'TRCK')
                metadata['genre'] = self._get_tag_value(audio_file, 'TCON')
                
            elif file_ext in ['.m4a', '.mp4']:
                # MP4/M4A
                metadata['title'] = self._get_tag_value(audio_file, '\xa9nam')
                metadata['artist'] = self._get_tag_value(audio_file, '\xa9ART')
                metadata['album'] = self._get_tag_value(audio_file, '\xa9alb')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'aART')
                metadata['date'] = self._get_tag_value(audio_file, '\xa9day')
                metadata['track'] = self._get_tag_value(audio_file, 'trkn')
                metadata['genre'] = self._get_tag_value(audio_file, '\xa9gen')
                
            elif file_ext == '.flac':
                # FLAC
                metadata['title'] = self._get_tag_value(audio_file, 'TITLE')
                metadata['artist'] = self._get_tag_value(audio_file, 'ARTIST')
                metadata['album'] = self._get_tag_value(audio_file, 'ALBUM')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'ALBUMARTIST')
                metadata['date'] = self._get_tag_value(audio_file, 'DATE')
                metadata['tracknumber'] = self._get_tag_value(audio_file, 'TRACKNUMBER')
                metadata['genre'] = self._get_tag_value(audio_file, 'GENRE')
                
            elif file_ext == '.ogg':
                # OGG Vorbis
                metadata['title'] = self._get_tag_value(audio_file, 'TITLE')
                metadata['artist'] = self._get_tag_value(audio_file, 'ARTIST')
                metadata['album'] = self._get_tag_value(audio_file, 'ALBUM')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'ALBUMARTIST')
                metadata['date'] = self._get_tag_value(audio_file, 'DATE')
                metadata['tracknumber'] = self._get_tag_value(audio_file, 'TRACKNUMBER')
                metadata['genre'] = self._get_tag_value(audio_file, 'GENRE')
            
            # Nettoyer et valider
            metadata = {k: v for k, v in metadata.items() if v and str(v).strip()}
            
            # Retourner seulement si on a au minimum titre + artiste
            if metadata.get('title') and metadata.get('artist'):
                return metadata
                
            return None
            
        except Exception as e:
            self.logger.debug(f"Metadata extraction error: {e}")
            return None
    
    def _get_tag_value(self, audio_file, tag_name: str) -> Optional[str]:
        """Extrait la valeur d'un tag de manière sécurisée"""
        try:
            if tag_name in audio_file and audio_file[tag_name]:
                value = audio_file[tag_name][0]
                return str(value).strip() if value else None
        except (IndexError, TypeError, AttributeError):
            pass
        return None
    
    def _generate_cache_key(self, file_path: str) -> str:
        """Génère une clé de cache unique pour le fichier"""
        file_stat = os.stat(file_path)
        key_data = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[AnalysisResult]:
        """Récupère un résultat depuis le cache"""
        try:
            cached_data = self.cache.get_cached_data('unified_analysis', cache_key)
            if cached_data:
                return AnalysisResult.from_dict(cached_data['data'])
        except Exception as e:
            self.logger.debug(f"Cache retrieval error: {e}")
        return None
    
    def _cache_result(self, cache_key: str, result: AnalysisResult):
        """Met en cache un résultat d'analyse"""
        try:
            self.cache.cache_data('unified_analysis', cache_key, result.to_dict())
        except Exception as e:
            self.logger.debug(f"Cache storage error: {e}")
    
    def _analyze_failure_reason(self, result: AnalysisResult) -> str:
        """Analyse pourquoi le traitement a échoué"""
        if not result.methods_attempted:
            return "Aucune méthode d'analyse n'a pu être tentée"
        
        if result.errors:
            return f"Erreurs rencontrées: {'; '.join(result.errors[:2])}"
        
        if len(result.methods_attempted) == len(AnalysisMethod):
            return "Toutes les méthodes ont échoué ou donné une confiance insuffisante"
        
        return "Raison indéterminée - vérifiez la qualité du fichier audio"
    
    def process_batch(self, file_paths: List[str], progress_callback=None) -> List[AnalysisResult]:
        """
        Traite un lot de fichiers
        
        Args:
            file_paths: Liste des chemins de fichiers
            progress_callback: Fonction appelée pour chaque fichier (optionnelle)
            
        Returns:
            List[AnalysisResult]: Résultats pour chaque fichier
        """
        results = []
        total_files = len(file_paths)
        
        self.logger.info(f"🎵 Traitement batch de {total_files} fichiers")
        
        for i, file_path in enumerate(file_paths):
            try:
                result = self.process_file(file_path)
                results.append(result)
                
                if progress_callback:
                    progress_callback(i + 1, total_files, result)
                    
            except Exception as e:
                error_result = AnalysisResult(
                    status=AnalysisStatus.FAILED,
                    file_path=file_path,
                    errors=[f"Erreur critique: {str(e)}"]
                )
                results.append(error_result)
                self.logger.error(f"Erreur sur {file_path}: {e}")
        
        self.logger.info(f"✅ Batch terminé: {len(results)} fichiers traités")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de la session"""
        total = self.stats['total_processed']
        return {
            'total_processed': total,
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': self.stats['cache_hits'] / total if total > 0 else 0,
            'acousticid_successes': self.stats['acousticid_successes'],
            'spectral_successes': self.stats['spectral_successes'],
            'musicbrainz_successes': self.stats['musicbrainz_successes'],
            'manual_reviews': self.stats['manual_reviews'],
            'errors': self.stats['errors'],
            'total_processing_time': self.stats['processing_time'],
            'average_processing_time': self.stats['processing_time'] / total if total > 0 else 0,
            'success_rate': (self.stats['acousticid_successes'] + self.stats['spectral_successes'] + self.stats['musicbrainz_successes']) / total if total > 0 else 0
        }
    
    def reset_statistics(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'acousticid_successes': 0,
            'spectral_successes': 0,
            'musicbrainz_successes': 0,
            'manual_reviews': 0,
            'errors': 0,
            'processing_time': 0.0
        }
        self.logger.info("📊 Statistiques remises à zéro")
    
    def configure_thresholds(self, **kwargs):
        """
        Configure les seuils de confiance
        
        Args:
            acousticid_threshold: Seuil pour AcoustID (0.0-1.0)
            spectral_threshold: Seuil pour l'analyse spectrale (0.0-1.0)
            musicbrainz_threshold: Seuil pour MusicBrainz (0.0-1.0)
        """
        # Mapping des noms d'arguments vers les clés de configuration
        threshold_mapping = {
            'acousticid_threshold': 'acousticid_min_confidence',
            'spectral_threshold': 'spectral_similarity_threshold',
            'musicbrainz_threshold': 'musicbrainz_min_confidence'
        }
        
        for key, value in kwargs.items():
            config_key = threshold_mapping.get(key, key)
            if config_key in self.thresholds:
                self.thresholds[config_key] = float(value)
                self.logger.info(f"🔧 Seuil {key} configuré à {value}")
                
                # Mettre à jour la configuration si possible
                try:
                    self.config.set('FINGERPRINT', config_key, str(value))
                except Exception as e:
                    self.logger.debug(f"Impossible de sauvegarder la config: {e}")

    def configure_api_key(self, api_key: str):
        """Configure la clé API AcoustID"""
        self.api_key = api_key
        self.logger.info("🔑 Clé API AcoustID configurée")
        
        # Mettre à jour la configuration si possible
        try:
            self.config.set('APIS', 'acoustid_api_key', api_key)
        except Exception as e:
            self.logger.debug(f"Impossible de sauvegarder la config: {e}")
    
    def clear_cache(self):
        """Vide le cache d'analyse"""
        try:
            self.cache.clear_cache('unified_analysis')
            self.logger.info("🧹 Cache d'analyse vidé")
        except Exception as e:
            self.logger.error(f"Erreur lors du vidage du cache: {e}")


# Fonction de convenance pour utilisation simple
def analyze_audio_file(file_path: str, api_key: str = None) -> AnalysisResult:
    """
    Fonction de convenance pour analyser un seul fichier
    
    Args:
        file_path: Chemin vers le fichier audio
        api_key: Clé API AcoustID (optionnelle)
        
    Returns:
        AnalysisResult: Résultat de l'analyse
    """
    processor = UnifiedAudioProcessor(api_key=api_key)
    return processor.process_file(file_path)


if __name__ == "__main__":
    # Test simple
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"🎵 Test du processeur unifié sur: {test_file}")
        
        processor = UnifiedAudioProcessor()
        result = processor.process_file(test_file)
        
        print(f"📊 Résultat: {result.status.value}")
        print(f"🎯 Méthode: {result.method_used.value if result.method_used else 'Aucune'}")
        print(f"📈 Confiance: {result.confidence:.2f}")
        print(f"⏱️ Temps: {result.processing_time:.2f}s")
        
        if result.metadata:
            print("🎵 Métadonnées trouvées:")
            for key, value in result.metadata.items():
                print(f"   {key}: {value}")
        
        if result.errors:
            print("❌ Erreurs:")
            for error in result.errors:
                print(f"   {error}")
        
        # Statistiques
        stats = processor.get_statistics()
        print(f"\n📊 Statistiques: {stats}")
    else:
        print("Usage: python unified_audio_processor.py <fichier_audio>")
