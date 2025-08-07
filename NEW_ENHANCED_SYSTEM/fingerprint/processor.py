import os
import logging
import time
import functools
import numpy as np
from pathlib import Path
from acoustid import fingerprint_file, lookup, parse_lookup_result
from .cache import AcoustIDCache
from .musicbrainz_search import MusicBrainzSearcher
from cache.cache_manager import CacheManager
from config.config_manager import ConfigManager

# Import de l'analyseur spectral
import sys
sys.path.append(str(Path(__file__).parent.parent))
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spectral_analyzer import SpectralMatcher

from errors import ErrorManager, get_error_manager, AudioProcessingError, ConfigurationError

# Configuration du chemin vers fpcalc.exe
CURRENT_DIR = Path(__file__).parent.parent
FPCALC_PATH = CURRENT_DIR / "audio_tools" / "fpcalc.exe"

# Définir la variable d'environnement pour pyacoustid
if FPCALC_PATH.exists():
    os.environ['FPCALC'] = str(FPCALC_PATH)
    print(f"✅ fpcalc configuré: {FPCALC_PATH}")
else:
    print(f"⚠️ fpcalc non trouvé: {FPCALC_PATH}")

def timer(func):
    """Décorateur pour mesurer le temps d'exécution"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        print(f"{func.__name__} exécuté en {execution_time:.2f}s")
        return result
    return wrapper



class AudioFingerprinter:
    def __init__(self, api_key, logger=None, max_retries=3):
        self.api_key = api_key
        self.cache = CacheManager.get_instance()
        self.acoustid_cache = AcoustIDCache()  # Garde l'ancien cache pour la compatibilité
        self.config = ConfigManager.get_instance()
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.error_manager = get_error_manager()
        
        # Nouveau système de recherche MusicBrainz
        self.musicbrainz_searcher = MusicBrainzSearcher(logger=self.logger)
        
        # Initialiser l'analyseur spectral
        try:
            spectral_threshold = self.config.getfloat('FINGERPRINT', 'spectral_similarity_threshold')
        except:
            spectral_threshold = 0.7  # Valeur par défaut
        self.spectral_matcher = SpectralMatcher(threshold=spectral_threshold)
        
        # Base de données de référence spectrale (pour l'instant vide, à implémenter)
        self.spectral_reference_db = {}
        
        # Enregistrer un gestionnaire personnalisé pour les erreurs audio
        self.error_manager.register_handler('audio_processor', self._handle_audio_error)
        
    def _handle_audio_error(self, error_entry):
        """Gestionnaire spécialisé pour les erreurs audio"""
        if error_entry['error_code'].startswith('AUDIO_'):
            self.logger.warning(f"Erreur audio traitée: {error_entry['message']}")

    def _extract_existing_metadata(self, file_path):
        """Extrait les métadonnées existantes d'un fichier audio de manière enrichie"""
        try:
            try:
                from mutagen import File
            except ImportError:
                return None
            
            audio_file = File(file_path)
            if not audio_file:
                return None
            
            metadata = {}
            
            # Extraction selon le format
            if file_path.lower().endswith('.mp3'):
                # MP3 avec ID3
                metadata['title'] = self._get_tag_value(audio_file, 'TIT2')
                metadata['artist'] = self._get_tag_value(audio_file, 'TPE1')
                metadata['album'] = self._get_tag_value(audio_file, 'TALB')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'TPE2')
                metadata['date'] = self._get_tag_value(audio_file, 'TDRC')
                metadata['track'] = self._get_tag_value(audio_file, 'TRCK')
                metadata['label'] = self._get_tag_value(audio_file, 'TPUB')
                metadata['catalognumber'] = self._get_custom_tag_value(audio_file, 'CATALOGNUMBER')
                metadata['musicbrainz_trackid'] = self._get_ufid_value(audio_file, 'http://musicbrainz.org')
                metadata['musicbrainz_albumid'] = self._get_custom_tag_value(audio_file, 'MusicBrainz Album Id')
            elif file_path.lower().endswith(('.m4a', '.mp4')):
                # MP4/M4A
                metadata['title'] = self._get_tag_value(audio_file, '\xa9nam')
                metadata['artist'] = self._get_tag_value(audio_file, '\xa9ART')
                metadata['album'] = self._get_tag_value(audio_file, '\xa9alb')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'aART')
                metadata['date'] = self._get_tag_value(audio_file, '\xa9day')
                metadata['track'] = self._get_tag_value(audio_file, 'trkn')
            elif file_path.lower().endswith('.flac'):
                # FLAC
                metadata['title'] = self._get_tag_value(audio_file, 'TITLE')
                metadata['artist'] = self._get_tag_value(audio_file, 'ARTIST')
                metadata['album'] = self._get_tag_value(audio_file, 'ALBUM')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'ALBUMARTIST')
                metadata['date'] = self._get_tag_value(audio_file, 'DATE')
                metadata['tracknumber'] = self._get_tag_value(audio_file, 'TRACKNUMBER')
                metadata['label'] = self._get_tag_value(audio_file, 'LABEL')
                metadata['catalognumber'] = self._get_tag_value(audio_file, 'CATALOGNUMBER')
            elif file_path.lower().endswith('.ogg'):
                # OGG Vorbis
                metadata['title'] = self._get_tag_value(audio_file, 'TITLE')
                metadata['artist'] = self._get_tag_value(audio_file, 'ARTIST')
                metadata['album'] = self._get_tag_value(audio_file, 'ALBUM')
                metadata['albumartist'] = self._get_tag_value(audio_file, 'ALBUMARTIST')
                metadata['date'] = self._get_tag_value(audio_file, 'DATE')
                metadata['tracknumber'] = self._get_tag_value(audio_file, 'TRACKNUMBER')
            
            # Filtrer les valeurs vides
            metadata = {k: v for k, v in metadata.items() if v and str(v).strip()}
            
            # Retourner seulement si on a au moins titre + artiste
            if metadata.get('title') and metadata.get('artist'):
                return metadata
                
            return None
            
        except Exception as e:
            self.logger.debug(f"Erreur lors de l'extraction des métadonnées: {e}")
            return None
    
    def _get_tag_value(self, audio_file, tag_name):
        """Extrait la valeur d'un tag de manière sécurisée"""
        try:
            if tag_name in audio_file and audio_file[tag_name]:
                return str(audio_file[tag_name][0]).strip()
        except (IndexError, TypeError):
            pass
        return None

    def _get_custom_tag_value(self, audio_file, desc):
        """Extrait la valeur d'un tag TXXX personnalisé pour MP3"""
        try:
            if hasattr(audio_file, 'tags') and audio_file.tags:
                for tag in audio_file.tags.values():
                    if hasattr(tag, 'desc') and tag.desc == desc:
                        return str(tag.text[0]).strip() if tag.text else None
        except:
            pass
        return None

    def _get_ufid_value(self, audio_file, owner):
        """Extrait la valeur d'un tag UFID pour MP3"""
        try:
            if hasattr(audio_file, 'tags') and audio_file.tags:
                ufid_key = f'UFID:{owner}'
                if ufid_key in audio_file.tags:
                    return audio_file.tags[ufid_key].data.decode('utf-8')
        except:
            pass
        return None
    
    def resolve_metadata(self, file_path):
        """Workflow complet de résolution des métadonnées"""
        try:
            return self._resolve_metadata_core(file_path)
        except Exception as e:
            self.logger.error(f"Échec du traitement: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _resolve_metadata_core(self, file_path):
        # Configuration des seuils
        min_confidence = self.config.getfloat('FINGERPRINT', 'acoustid_min_confidence')
        
        # Essayer d'abord avec AcoustID
        try:
            acoustid_data = self._get_acoustid_data(file_path)
            
            # Détails pour le diagnostic
            acoustid_confidence = acoustid_data.get('confidence', 0) if acoustid_data else 0
            self.logger.info(f"AcoustID confiance: {acoustid_confidence:.3f} (seuil: {min_confidence})")
            
            if acoustid_data and acoustid_confidence > min_confidence:
                return self._handle_acoustid_match(file_path, acoustid_data)
        except Exception as e:
            self.logger.warning(f"AcoustID échec: {e}")
            acoustid_data = None
            acoustid_confidence = 0
        
        # Fallback spectral
        spectral_data = self._spectral_fallback(file_path)
        spectral_threshold = self.config.getfloat('FINGERPRINT', 'spectral_similarity_threshold')
        
        if spectral_data.get('similarity', 0) > spectral_threshold:
            return self._handle_spectral_match(file_path, spectral_data)
        
        # NOUVEAU: Fallback MusicBrainz - essayer d'abord avec les métadonnées existantes
        self.logger.info("🔍 Tentative de recherche MusicBrainz par métadonnées existantes...")
        existing_metadata = self._extract_existing_metadata(file_path)
        musicbrainz_data = None
        
        if existing_metadata:
            self.logger.info(f"📊 Métadonnées trouvées: {existing_metadata}")
            musicbrainz_data = self.musicbrainz_searcher.search_by_metadata(existing_metadata)
            if musicbrainz_data:
                self.logger.info("✨ Correspondance trouvée via métadonnées existantes")
            else:
                self.logger.info("❌ Aucune correspondance MusicBrainz via métadonnées")
        else:
            self.logger.info("⚠️ Aucune métadonnée exploitable trouvée")
        
        # Si pas de résultat avec métadonnées, essayer par nom de fichier
        if not musicbrainz_data:
            self.logger.info("🔍 Tentative de recherche MusicBrainz par nom de fichier...")
            musicbrainz_data = self.musicbrainz_searcher.search_by_filename(file_path)
        
        musicbrainz_threshold = self.config.getfloat('FINGERPRINT', 'musicbrainz_min_confidence')
        
        # Vérifier la confiance (nouveau format avec suggestions ou ancien format)
        best_confidence = 0
        if musicbrainz_data:
            if 'best_match' in musicbrainz_data:
                best_confidence = musicbrainz_data['best_match'].get('confidence', 0)
            else:
                best_confidence = musicbrainz_data.get('confidence', 0)
        
        if musicbrainz_data and best_confidence > musicbrainz_threshold:
            return self._handle_musicbrainz_match(file_path, musicbrainz_data)
        
        # Analyser pourquoi la révision manuelle est nécessaire
        reason_details = self._analyze_manual_review_reason(acoustid_data, acoustid_confidence, min_confidence)
        
        # Demander intervention UI avec détails détaillés, inclure suggestions MusicBrainz
        return {
            'status': 'manual_review',
            'file_path': file_path,
            'reason': reason_details['reason'],
            'details': reason_details['details'],
            'suggested_actions': reason_details['actions'],
            'acoustid_data': acoustid_data,  # Données pour inspection manuelle
            'musicbrainz_suggestions': musicbrainz_data,  # Suggestions MusicBrainz même si confiance faible
            'confidence': acoustid_confidence
        }
    
    def _analyze_manual_review_reason(self, acoustid_data, confidence, min_confidence):
        """Analyse pourquoi une révision manuelle est nécessaire"""
        
        if not acoustid_data:
            return {
                'reason': 'Aucune correspondance trouvée',
                'details': 'Le fichier audio n\'a donné aucun résultat dans la base de données AcoustID',
                'actions': [
                    'Vérifier que le fichier audio est de bonne qualité',
                    'Essayer avec une autre source ou version du fichier',
                    'Saisir les métadonnées manuellement',
                    'Diminuer le seuil de confiance dans la configuration'
                ]
            }
        
        if confidence < min_confidence:
            confidence_percent = confidence * 100
            threshold_percent = min_confidence * 100
            
            metadata = acoustid_data.get('metadata', {})
            suggested_title = metadata.get('title', 'Inconnu')
            suggested_artist = metadata.get('artists', [{}])[0].get('name', 'Inconnu') if metadata.get('artists') else 'Inconnu'
            
            return {
                'reason': f'Confiance insuffisante ({confidence_percent:.1f}% < {threshold_percent:.1f}%)',
                'details': f'AcoustID suggère: "{suggested_artist} - {suggested_title}" mais avec une confiance de seulement {confidence_percent:.1f}%',
                'actions': [
                    f'Vérifier si "{suggested_artist} - {suggested_title}" correspond au fichier',
                    'Accepter la suggestion si elle semble correcte',
                    'Chercher manuellement les bonnes métadonnées',
                    'Diminuer le seuil de confiance si les suggestions sont souvent correctes'
                ]
            }
        
        return {
            'reason': 'Raison inconnue',
            'details': 'Le système n\'a pas pu déterminer pourquoi une révision manuelle est nécessaire',
            'actions': ['Contacter le support technique']
        }
    
    def _get_acoustid_data(self, file_path):
        cached_data = self.acoustid_cache.get(file_path)
        if cached_data:
            return self._query_acoustid_api(cached_data)
        
        return self._generate_and_query(file_path)
    
    def _generate_and_query(self, file_path):
        audio_length, fingerprint = self._generate_fingerprint(file_path)
        result = self._query_acoustid_api((audio_length, fingerprint, None))
        
        # Mettre en cache l'empreinte pour éviter la regénération
        if result and result.get('track_id'):
            self.acoustid_cache.set(file_path, audio_length, fingerprint, result['track_id'])
            
        return result
    
    def _generate_fingerprint(self, file_path):
        """Génère l'empreinte acoustique avec Chromaprint"""
        try:
            # Vérifier que fpcalc est disponible
            if 'FPCALC' not in os.environ:
                if FPCALC_PATH.exists():
                    os.environ['FPCALC'] = str(FPCALC_PATH)
                else:
                    error = self.error_manager.create_audio_error(
                        f"fpcalc.exe non trouvé dans {FPCALC_PATH}",
                        file_path=file_path
                    )
                    raise error
            
            # Vérifier que le fichier existe et est lisible
            if not os.path.exists(file_path):
                error = self.error_manager.create_audio_error(
                    f"Fichier non trouvé: {file_path}",
                    file_path=file_path
                )
                raise error
            
            if not os.access(file_path, os.R_OK):
                error = AudioProcessingError(
                    f"Fichier non lisible: {file_path}",
                    file_path=file_path,
                    error_code="FILE_001"  # Permission denied
                )
                raise error
            
            # Vérifier la taille du fichier
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                error = self.error_manager.create_audio_error(
                    f"Fichier vide: {file_path}",
                    file_path=file_path
                )
                raise error
            
            self.logger.info(f"Analyse de {os.path.basename(file_path)} ({file_size} bytes)")
            
            audio_length, fingerprint = fingerprint_file(file_path)
            return audio_length, fingerprint
            
        except AudioProcessingError:
            # Re-lancer les erreurs déjà typées
            raise
        except Exception as e:
            error_msg = str(e)
            
            # Diagnostiquer l'erreur de fpcalc et créer l'erreur appropriée
            if "fpcalc exited with status 2" in error_msg:
                # Status 2 = fichier audio invalide ou corrompu
                error = self.error_manager.create_audio_error(
                    f"Fichier audio invalide ou corrompu: {os.path.basename(file_path)}",
                    file_path=file_path,
                    fpcalc_status=2
                )
                # Gérer l'erreur via le manager
                self.error_manager.handle_error(error, {'file_path': file_path, 'operation': 'fingerprint'})
                raise error
                
            elif "fpcalc exited with status 1" in error_msg:
                # Status 1 = erreur de format
                error = self.error_manager.create_audio_error(
                    f"Format audio non supporté: {os.path.basename(file_path)}",
                    file_path=file_path,
                    fpcalc_status=1
                )
                self.error_manager.handle_error(error, {'file_path': file_path, 'operation': 'fingerprint'})
                raise error
                
            else:
                # Erreur générique
                error = self.error_manager.create_audio_error(
                    f"Erreur de génération d'empreinte: {error_msg}",
                    file_path=file_path
                )
                self.error_manager.handle_error(error, {'file_path': file_path, 'operation': 'fingerprint'})
                raise error
    
    def _query_acoustid_api(self, data):
        audio_length, fingerprint, track_id = data
        for attempt in range(self.max_retries):
            try:
                results = lookup(
                    self.api_key, 
                    fingerprint, 
                    audio_length
                )
                
                # Traitement des résultats
                if results.get('results'):
                    best_match = max(results['results'], key=lambda x: x['score'])
                    track_id = best_match['id']
                    
                    # Vérification sécurisée des recordings
                    recordings = best_match.get('recordings', [])
                    if not recordings:
                        self.logger.warning(f"Aucun recording trouvé pour track_id: {track_id}")
                        return {
                            'track_id': track_id,
                            'confidence': best_match['score'],
                            'metadata': {}  # Métadonnées vides si pas de recordings
                        }
                    
                    return {
                        'track_id': track_id,
                        'confidence': best_match['score'],
                        'metadata': recordings[0]
                    }
                else:
                    self.logger.info("Aucun résultat AcoustID trouvé")
                    return None
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Tentative {attempt + 1} échouée, retry...")
                    continue
                raise RuntimeError(f"Erreur API AcoustID: {str(e)}")
        return None
    
    def _spectral_fallback(self, file_path):
        """Méthode de fallback spectral - maintenant réellement implémentée !"""
        try:
            self.logger.info(f"🔍 Analyse spectrale de {os.path.basename(file_path)}...")
            
            # Pour l'instant, comme nous n'avons pas de base de données de référence spectrale,
            # nous simulons un processus d'analyse spectrale basique
            
            # Si nous avons une base de données de référence spectrale
            if self.spectral_reference_db:
                match_id, similarity = self.spectral_matcher.is_match(
                    self.spectral_reference_db, 
                    file_path
                )
                
                if match_id and similarity > self.spectral_matcher.threshold:
                    # Convertir en float pour éviter les erreurs de format numpy
                    similarity_float = float(similarity)
                    self.logger.info(f"✅ Correspondance spectrale trouvée: {similarity_float:.2%}")
                    return {
                        'track_id': match_id,
                        'similarity': similarity_float,
                        'metadata': self._get_spectral_metadata(match_id),
                        'note': 'Correspondance spectrale trouvée'
                    }
            
            # Analyse spectrale basique sans référence (extraction de caractéristiques)
            try:
                import librosa
                y, sr = librosa.load(file_path, duration=30)  # Analyser les 30 premières secondes
                
                # Extraire des caractéristiques spectrales
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                
                # Caractéristiques moyennes
                avg_mfcc = np.mean(mfcc, axis=1)
                avg_spectral_centroid = np.mean(spectral_centroid)
                
                # Pour l'instant, nous ne pouvons pas faire de matching sans base de référence
                # Mais nous collectons les données pour un futur usage
                spectral_features = {
                    'mfcc_mean': avg_mfcc.tolist(),
                    'spectral_centroid_mean': float(avg_spectral_centroid),
                    'tempo': float(tempo),
                    'duration_analyzed': 30
                }
                
                self.logger.info(f"📊 Caractéristiques spectrales extraites (tempo: {float(tempo):.1f} BPM)")
                
                # Pour l'instant, retourner une similarité faible car pas de référence
                return {
                    'track_id': None,
                    'similarity': 0.2,  # Similarité faible car pas de matching possible
                    'features': spectral_features,
                    'metadata': None,
                    'note': 'Caractéristiques extraites mais pas de base de référence pour le matching'
                }
                
            except ImportError:
                self.logger.warning("📊 Librosa non disponible pour l'analyse spectrale")
                return {
                    'track_id': None,
                    'similarity': 0.0,
                    'metadata': None,
                    'note': 'Librosa requis pour l\'analyse spectrale'
                }
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse spectrale: {e}")
            return {
                'track_id': None,
                'similarity': 0.0,
                'metadata': None,
                'note': f'Erreur: {str(e)}'
            }
    
    def _get_spectral_metadata(self, track_id):
        """Récupère les métadonnées pour un ID de track spectral"""
        # Placeholder pour récupérer les métadonnées depuis la base spectrale
        # À implémenter quand nous aurons une vraie base de données spectrale
        return {
            'title': f'Titre spectral {track_id}',
            'artist': 'Artiste spectral',
            'source': 'spectral_analysis'
        }
    
    def _handle_spectral_match(self, file_path, data):
        """Traite une correspondance spectrale"""
        return {
            'status': 'spectral_success',
            'file_path': file_path,
            'track_id': data['track_id'],
            'similarity': data['similarity'],
            'updates': self._format_updates(data['metadata']),
            'features': data.get('features', {}),
            'note': data.get('note', '')
        }

    def _handle_acoustid_match(self, file_path, data):
        """Mise à jour des tags avec les données AcoustID"""
        # Ici: intégration avec le système de tagging
        return {
            'status': 'acoustid_success',
            'file_path': file_path,
            'track_id': data['track_id'],
            'confidence': data['confidence'],
            'updates': self._format_updates(data['metadata'])
        }
    
    def _handle_musicbrainz_match(self, file_path, data):
        """Gère les correspondances trouvées via recherche MusicBrainz"""
        # Debug logging
        self.logger.debug(f"_handle_musicbrainz_match reçu: {type(data)} - clés: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        
        best_match = None
        
        # Gérer le nouveau format avec plusieurs suggestions
        if 'suggestions' in data and data['suggestions']:
            best_match = data['best_match']
            self.logger.debug(f"Nouveau format - best_match: {type(best_match)} - clés: {list(best_match.keys()) if isinstance(best_match, dict) else 'N/A'}")
        elif 'best_match' in data:
            # Format avec best_match mais sans suggestions
            best_match = data['best_match']
            self.logger.debug(f"Format best_match - best_match: {type(best_match)} - clés: {list(best_match.keys()) if isinstance(best_match, dict) else 'N/A'}")
        else:
            # Format ancien (rétrocompatibilité) - vérifier la structure
            self.logger.debug(f"Format ancien - data: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            if 'recording' in data:
                # data contient directement un recording - wrapper dans best_match format
                best_match = {'recording': data['recording'], 'confidence': data.get('confidence', 0)}
            else:
                self.logger.warning(f"Format de données MusicBrainz non reconnu: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return {'status': 'failed', 'error': 'Format de données MusicBrainz non reconnu'}
        
        # Vérifier que best_match est valide
        if not best_match:
            self.logger.warning("best_match est None ou vide")
            return {'status': 'failed', 'error': 'Aucune correspondance MusicBrainz valide'}
        
        formatted_metadata = self.musicbrainz_searcher.format_result(best_match)
        
        if not formatted_metadata:
            return {'status': 'failed', 'error': 'Impossible de formater les données MusicBrainz'}
        
        confidence = data.get('confidence', 0)
        if 'best_match' in data and data['best_match']:
            confidence = data['best_match'].get('confidence', 0)
        
        self.logger.info(f"✅ MusicBrainz: {formatted_metadata['artist']} - {formatted_metadata['title']}")
        
        return {
            'status': 'musicbrainz_success',
            'file_path': file_path,
            'musicbrainz_id': formatted_metadata.get('musicbrainz_id', ''),
            'confidence': confidence,
            'updates': formatted_metadata,
            'source': 'musicbrainz_text_search'
        }
    
    def _format_updates(self, metadata):
        """Format les métadonnées pour mise à jour"""
        return {
            'title': metadata.get('title', ''),
            'artist': metadata.get('artists', [{}])[0].get('name', ''),
            'album': metadata.get('release', {}).get('title', '')
        }
    
    @timer
    def get_fingerprint(self, file_path):
        """Version simplifiée et vérifiée avec cache robuste"""
        return self.cache.caching(self._get_fingerprint_core)(file_path)
    
    def _get_fingerprint_core(self, file_path):
        """Logique core du fingerprint (sans cache)"""
        # Méthode directe avec pyacoustid
        duration, fingerprint = fingerprint_file(file_path)
        
        return {
            'duration': duration,
            'fingerprint': fingerprint,
            'file_path': file_path
        }

    def query_acoustid(self, fingerprint, duration):
        """Recherche dans la base AcoustID"""
        results = lookup(
            apikey=self.api_key,
            fingerprint=fingerprint,
            duration=duration
        )
        # Traitement minimal des résultats
        return parse_lookup_result(results)