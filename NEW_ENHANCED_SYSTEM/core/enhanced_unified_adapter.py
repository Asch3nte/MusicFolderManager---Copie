#!/usr/bin/env python3
"""
Adaptateur Interface Utilisateur pour le Processeur Audio Unifié - Version Complète
Compatible avec l'interface existante de MusicFolderManager avec toutes les fonctionnalités
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import json
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path

from core.unified_audio_processor import UnifiedAudioProcessor, AnalysisResult, AnalysisStatus, AnalysisMethod
from utils.file_utils import is_audio_file
from cache.cache_manager import CacheManager
from backup.backup_handler import BackupHandler

class EnhancedUnifiedProcessorAdapter:
    """
    Adaptateur complet pour intégrer le processeur unifié avec l'interface existante
    
    Fonctionnalités réimplémentées:
    - Système de cache complet
    - Détection et bypass des fichiers corrompus
    - Sélection manuelle des résultats MusicBrainz
    - Contrôle d'arrêt du traitement
    - Cases à cocher pour sélection de fichiers
    - Gestion des erreurs avancée
    """
    
    def __init__(self, config_manager=None, logger=None):
        """
        Initialise l'adaptateur avec toutes les fonctionnalités
        
        Args:
            config_manager: Gestionnaire de configuration existant
            logger: Logger existant
        """
        self.config = config_manager
        self.logger = logger
        
        # Initialiser les gestionnaires
        self.cache_manager = CacheManager.get_instance()
        self.backup_handler = BackupHandler()
        
        # Récupérer la clé API depuis la configuration
        api_key = None
        if self.config:
            api_key = self.config.get('APIS', 'acoustid_api_key', fallback='')
        
        # Initialiser le processeur unifié
        self.processor = UnifiedAudioProcessor(api_key=api_key)
        
        # Configurer un logger personnalisé qui redirige vers l'interface
        self._setup_processor_logging()
        
        # Callbacks pour l'interface
        self.progress_callback = None
        self.status_callback = None
        self.result_callback = None
        self.manual_selection_callback = None
        
        # État du traitement
        self.is_processing = False
        self.stop_requested = False
        self.current_results = []
        self.processing_thread = None
        
        # Configuration avancée
        self.skip_corrupted_files = True
        self.enable_manual_selection = True
        self.enable_deep_cache = True
        
        # Fichiers sélectionnés (pour les cases à cocher)
        self.selected_files = set()
        
        # Statistiques détaillées
        self.detailed_stats = {
            'corrupted_files': [],
            'manual_selections': [],
            'cache_usage': {},
            'method_performance': {}
        }
        
        # Charger la configuration avancée
        self._load_advanced_config()
        
        if self.logger:
            self.logger.info("🎵 Adaptateur Enhanced Unified Processor initialisé")
    
    def _load_advanced_config(self):
        """Charge la configuration avancée depuis les paramètres"""
        try:
            if self.config:
                self.skip_corrupted_files = self.config.getboolean('PROCESSING', 'skip_corrupted_files', fallback=True)
                self.enable_manual_selection = self.config.getboolean('PROCESSING', 'enable_manual_selection', fallback=True)
                self.enable_deep_cache = self.config.getboolean('CACHE', 'enable_deep_cache', fallback=True)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Erreur chargement config avancée: {e}")
    
    def set_callbacks(self, progress_callback: Callable = None, 
                     status_callback: Callable = None,
                     result_callback: Callable = None,
                     manual_selection_callback: Callable = None):
        """
        Configure les callbacks pour l'interface utilisateur
        
        Args:
            progress_callback: Fonction(current, total, result) pour la progression
            status_callback: Fonction(message, level="INFO") pour les messages de statut avec niveaux
            result_callback: Fonction(results) pour les résultats finaux
            manual_selection_callback: Fonction(file_path, candidates) pour sélection manuelle
        """
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.result_callback = result_callback
        self.manual_selection_callback = manual_selection_callback
    
    def _log(self, message: str, level: str = "INFO"):
        """Helper pour envoyer des logs avec niveaux à l'interface"""
        if self.status_callback:
            try:
                self.status_callback(message, level)
            except TypeError:
                # Fallback pour les anciens callbacks sans paramètre level
                self.status_callback(message)
        
        if self.logger:
            if level == "ERROR":
                self.logger.error(message)
            elif level == "WARNING":
                self.logger.warning(message)
            else:
                self.logger.info(message)
    
    def _setup_processor_logging(self):
        """Configure le logging du processeur pour rediriger vers l'interface"""
        import logging
        
        # Créer un handler personnalisé qui redirige vers l'interface
        class InterfaceLogHandler(logging.Handler):
            def __init__(self, adapter):
                super().__init__()
                self.adapter = adapter
            
            def emit(self, record):
                message = self.format(record)
                
                # Déterminer le niveau de log en fonction du contenu
                level = "INFO"
                if "ERROR" in message or "❌" in message or "💥" in message:
                    level = "ERROR"
                elif "WARNING" in message or "⚠️" in message:
                    level = "WARNING"
                elif "spectral" in message.lower() or "📈" in message or "📊" in message or "🌊" in message:
                    level = "SPECTRAL"
                elif "api" in message.lower() or "🌐" in message or "fingerprint" in message.lower() or "🎧" in message:
                    level = "API"
                elif "✅" in message:
                    level = "SUCCESS"
                elif "cache" in message.lower() or "💾" in message:
                    level = "CACHE"
                elif "fingerprint" in message.lower() or "🎵" in message:
                    level = "FINGERPRINT"
                
                # Envoyer vers l'interface
                self.adapter._log(message, level)
        
        # Ajouter le handler au logger du processeur
        handler = InterfaceLogHandler(self)
        handler.setLevel(logging.INFO)
        self.processor.logger.addHandler(handler)
        self.processor.logger.setLevel(logging.INFO)
    
    def configure_api_key(self, api_key: str):
        """Configure la clé API AcoustID"""
        self.processor.configure_api_key(api_key)
        if self.config:
            self.config.set('APIS', 'acoustid_api_key', api_key)
        
        if self.status_callback:
            self.status_callback("🔑 Clé API AcoustID configurée")
    
    def configure_thresholds(self, **kwargs):
        """Configure les seuils de confiance avec mapping correct"""
        # Mapping pour la compatibilité avec l'interface
        threshold_mapping = {
            'acousticid_threshold': 'acousticid_min_confidence',
            'spectral_threshold': 'spectral_similarity_threshold', 
            'musicbrainz_threshold': 'musicbrainz_min_confidence'
        }
        
        mapped_kwargs = {}
        for key, value in kwargs.items():
            mapped_key = threshold_mapping.get(key, key)
            mapped_kwargs[mapped_key] = value
        
        if mapped_kwargs:
            self.processor.configure_thresholds(**mapped_kwargs)
            
            if self.status_callback:
                self.status_callback("⚙️ Seuils de confiance mis à jour")
    
    def configure_processing_options(self, skip_corrupted: bool = None, 
                                   enable_manual_selection: bool = None,
                                   enable_deep_cache: bool = None):
        """Configure les options de traitement avancées"""
        if skip_corrupted is not None:
            self.skip_corrupted_files = skip_corrupted
        if enable_manual_selection is not None:
            self.enable_manual_selection = enable_manual_selection
        if enable_deep_cache is not None:
            self.enable_deep_cache = enable_deep_cache
        
        # Sauvegarder dans la config
        if self.config:
            try:
                self.config.set('PROCESSING', 'skip_corrupted_files', str(self.skip_corrupted_files))
                self.config.set('PROCESSING', 'enable_manual_selection', str(self.enable_manual_selection))
                self.config.set('CACHE', 'enable_deep_cache', str(self.enable_deep_cache))
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Erreur sauvegarde config: {e}")
    
    def scan_directory(self, directory: str) -> List[str]:
        """
        Scanne un répertoire pour trouver les fichiers audio avec détection de corruption
        
        Args:
            directory: Chemin du répertoire à scanner
            
        Returns:
            List[str]: Liste des fichiers audio trouvés (sans les corrompus si activé)
        """
        audio_files = []
        corrupted_files = []
        
        # Messages de statut
        if self.status_callback:
            self.status_callback(f"🔍 Scan du répertoire: {directory}", "INFO")
        
        try:
            # Utiliser os.walk comme dans l'ancienne interface (méthode éprouvée)
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        # Vérifier si le fichier est corrompu
                        if self.skip_corrupted_files and self._is_file_corrupted(file_path):
                            corrupted_files.append(file_path)
                            if self.logger:
                                self.logger.warning(f"Fichier corrompu ignoré: {Path(file_path).name}")
                            self._log(f"⚠️ Fichier corrompu ignoré: {Path(file_path).name}", "WARNING")
                        else:
                            audio_files.append(file_path)
                            # Log détaillé pour chaque fichier trouvé
                            self._log(f"✅ Fichier détecté: {Path(file_path).name}", "SUCCESS")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur lors du scan: {e}")
            self._log(f"❌ Erreur de scan: {e}", "ERROR")
        
        # Sauvegarder les statistiques
        self.detailed_stats['corrupted_files'] = corrupted_files
        
        # Messages de statut finaux
        self._log(f"📁 {len(audio_files)} fichiers audio trouvés", "SUCCESS")
        if corrupted_files:
            self._log(f"⚠️ {len(corrupted_files)} fichiers corrompus ignorés", "WARNING")
        
        return audio_files
    
    def _is_file_corrupted(self, file_path: str) -> bool:
        """
        Vérifie si un fichier audio est corrompu
        
        Args:
            file_path: Chemin du fichier à vérifier
            
        Returns:
            bool: True si le fichier est corrompu
        """
        try:
            # Vérifications de base
            if not os.path.exists(file_path):
                if self.logger:
                    self.logger.debug(f"Fichier inexistant: {file_path}")
                return True
            
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # Fichier trop petit (moins de 1KB)
                if self.logger:
                    self.logger.debug(f"Fichier trop petit ({file_size} bytes): {Path(file_path).name}")
                return True
            
            # Test de lecture des métadonnées avec mutagen (optionnel)
            try:
                from mutagen import File
                audio_file = File(file_path)
                if audio_file is None:
                    if self.logger:
                        self.logger.debug(f"Mutagen ne peut pas lire: {Path(file_path).name}")
                    # Ne pas considérer comme corrompu si mutagen ne peut pas lire
                    # Cela peut être dû à un format non supporté
                    return False
            except ImportError:
                # Mutagen pas installé, ignorer ce test
                if self.logger:
                    self.logger.debug("Mutagen non disponible, test de corruption ignoré")
                return False
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Erreur mutagen pour {Path(file_path).name}: {e}")
                return False
            
            # Pour les MP3, vérifier l'intégrité de base (simplifié)
            if file_path.lower().endswith('.mp3'):
                try:
                    with open(file_path, 'rb') as f:
                        header = f.read(10)
                        if len(header) < 10:
                            return True
                        # Vérifier le sync word MP3 (simplifié)
                        if not (header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
                            return False  # Ne pas être trop strict
                except Exception:
                    return False  # En cas d'erreur, ne pas marquer comme corrompu
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Erreur test corruption {Path(file_path).name}: {e}")
            return False  # En cas d'erreur, considérer comme non corrompu
    
    def set_file_selection(self, file_path: str, selected: bool):
        """
        Définit l'état de sélection d'un fichier (pour les cases à cocher)
        
        Args:
            file_path: Chemin du fichier
            selected: État de sélection
        """
        if selected:
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)
    
    def get_selected_files(self) -> List[str]:
        """Retourne la liste des fichiers sélectionnés"""
        return list(self.selected_files)
    
    def select_all_files(self, file_paths: List[str]):
        """Sélectionne tous les fichiers"""
        self.selected_files = set(file_paths)
    
    def clear_selection(self):
        """Désélectionne tous les fichiers"""
        self.selected_files.clear()
    
    def process_files_async(self, file_paths: List[str] = None, enable_methods: Dict[str, bool] = None):
        """
        Traite une liste de fichiers de manière asynchrone
        
        Args:
            file_paths: Liste des chemins de fichiers (None = utiliser la sélection)
            enable_methods: Dict des méthodes à activer/désactiver
        """
        if self.is_processing:
            if self.status_callback:
                self.status_callback("⚠️ Traitement déjà en cours")
            return
        
        # Utiliser les fichiers sélectionnés si aucune liste fournie
        if file_paths is None:
            file_paths = self.get_selected_files()
        
        if not file_paths:
            if self.status_callback:
                self.status_callback("⚠️ Aucun fichier sélectionné pour l'analyse")
            return
        
        # Configurer les méthodes à utiliser
        methods = self._configure_methods(enable_methods or {})
        
        # Réinitialiser l'état
        self.stop_requested = False
        self.current_results = []
        
        # Lancer le traitement dans un thread séparé
        self.processing_thread = threading.Thread(
            target=self._process_files_worker,
            args=(file_paths, methods),
            daemon=True
        )
        self.processing_thread.start()
    
    def stop_processing(self):
        """Arrête le traitement en cours"""
        if self.is_processing:
            self.stop_requested = True
            if self.status_callback:
                self.status_callback("🛑 Arrêt du traitement demandé...")
    
    def _configure_methods(self, enable_methods: Dict[str, bool]) -> List[AnalysisMethod]:
        """Configure la liste des méthodes à utiliser"""
        all_methods = [
            AnalysisMethod.ACOUSTICID,
            AnalysisMethod.SPECTRAL,
            AnalysisMethod.MUSICBRAINZ,
            AnalysisMethod.METADATA_EXTRACTION
        ]
        
        # Si pas de configuration spécifique, utiliser toutes les méthodes
        if not enable_methods:
            return all_methods
        
        # Filtrer selon la configuration
        enabled_methods = []
        method_mapping = {
            'acousticid': AnalysisMethod.ACOUSTICID,
            'spectral': AnalysisMethod.SPECTRAL,
            'musicbrainz': AnalysisMethod.MUSICBRAINZ,
            'metadata': AnalysisMethod.METADATA_EXTRACTION
        }
        
        for method_name, enabled in enable_methods.items():
            if enabled and method_name in method_mapping:
                enabled_methods.append(method_mapping[method_name])
        
        return enabled_methods or all_methods
    
    def _process_files_worker(self, file_paths: List[str], methods: List[AnalysisMethod]):
        """
        Worker pour le traitement des fichiers dans un thread séparé
        
        Args:
            file_paths: Liste des fichiers à traiter
            methods: Méthodes d'analyse à utiliser
        """
        self.is_processing = True
        total_files = len(file_paths)
        
        try:
            self._log(f"🚀 Début du traitement de {total_files} fichiers", "INFO")
            self._log(f"🎯 Méthodes activées: {', '.join([m.value for m in methods])}", "INFO")
            
            for i, file_path in enumerate(file_paths):
                # Vérifier si arrêt demandé
                if self.stop_requested:
                    self._log("🛑 Traitement arrêté par l'utilisateur", "WARNING")
                    break
                
                try:
                    filename = Path(file_path).name
                    self._log(f"📁 Traitement fichier {i+1}/{total_files}: {filename}", "INFO")
                    
                    # Vérifier le cache en profondeur si activé
                    cached_result = None
                    if self.enable_deep_cache:
                        cached_result = self._get_deep_cached_result(file_path)
                    
                    if cached_result:
                        result = cached_result
                        self._log(f"💾 Résultat trouvé en cache pour: {filename}", "CACHE")
                    else:
                        # Traitement normal avec logs détaillés
                        self._log(f"� Début analyse complète: {filename}", "INFO")
                        
                        # Le processeur va maintenant logger automatiquement ses étapes
                        result = self.processor.process_file(file_path, methods)
                        
                        # Log du résultat final
                        if result.status == AnalysisStatus.SUCCESS:
                            self._log(f"✅ Analyse réussie ({result.method_used.value}): {filename}", "SUCCESS")
                            if result.metadata.get('artist') and result.metadata.get('title'):
                                self._log(f"🎵 Métadonnées: {result.metadata['artist']} - {result.metadata['title']}", "SUCCESS")
                        elif result.status == AnalysisStatus.MANUAL_REVIEW:
                            self._log(f"🔍 Révision manuelle requise: {filename}", "WARNING")
                        else:
                            self._log(f"❌ Échec analyse: {filename}", "ERROR")
                        
                        # Sauvegarder en cache profond
                        if self.enable_deep_cache and result.status == AnalysisStatus.SUCCESS:
                            self._save_deep_cached_result(file_path, result)
                            self._log(f"💾 Résultat mis en cache: {filename}", "CACHE")
                    
                    # Si MusicBrainz et sélection manuelle activée
                    if (result.method_used == AnalysisMethod.MUSICBRAINZ and 
                        self.enable_manual_selection and 
                        self.manual_selection_callback):
                        result = self._handle_manual_selection(file_path, result)
                    
                    self.current_results.append(result)
                    
                    # Callback de progression
                    if self.progress_callback:
                        self.progress_callback(i + 1, total_files, result)
                
                except Exception as e:
                    error_result = AnalysisResult(
                        status=AnalysisStatus.FAILED,
                        file_path=file_path,
                        errors=[f"Erreur: {str(e)}"]
                    )
                    self.current_results.append(error_result)
                    
                    if self.logger:
                        self.logger.error(f"Erreur traitement {file_path}: {e}")
            
            # Traitement terminé
            if not self.stop_requested:
                if self.status_callback:
                    success_count = sum(1 for r in self.current_results if r.status == AnalysisStatus.SUCCESS)
                    self.status_callback(f"✅ Traitement terminé: {success_count}/{len(self.current_results)} succès")
                
                if self.result_callback:
                    self.result_callback(self.current_results)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur critique dans le worker: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erreur critique: {e}")
        
        finally:
            self.is_processing = False
    
    def _get_deep_cached_result(self, file_path: str) -> Optional[AnalysisResult]:
        """Récupère un résultat depuis le cache profond"""
        try:
            # Générer une clé de cache basée sur le fichier
            import hashlib
            file_stat = os.stat(file_path)
            cache_key = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Chercher dans le cache
            cached_data = self.cache_manager.get_cached_data('deep_analysis', cache_hash)
            if cached_data:
                return AnalysisResult.from_dict(cached_data['data'])
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Erreur cache profond: {e}")
        
        return None
    
    def _save_deep_cached_result(self, file_path: str, result: AnalysisResult):
        """Sauvegarde un résultat dans le cache profond"""
        try:
            # Générer une clé de cache basée sur le fichier
            import hashlib
            file_stat = os.stat(file_path)
            cache_key = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Sauvegarder dans le cache
            self.cache_manager.cache_data('deep_analysis', cache_hash, result.to_dict())
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Erreur sauvegarde cache: {e}")
    
    def _handle_manual_selection(self, file_path: str, result: AnalysisResult) -> AnalysisResult:
        """
        Gère la sélection manuelle pour les résultats MusicBrainz
        
        Args:
            file_path: Chemin du fichier
            result: Résultat initial
            
        Returns:
            AnalysisResult: Résultat modifié ou original
        """
        try:
            # Récupérer les candidats MusicBrainz
            candidates = self._get_musicbrainz_candidates(file_path)
            
            if len(candidates) > 1:
                # Appeler le callback de sélection manuelle
                selected_candidate = self.manual_selection_callback(file_path, candidates)
                
                if selected_candidate and selected_candidate != result.metadata:
                    # Créer un nouveau résultat avec les données sélectionnées
                    new_result = AnalysisResult(
                        status=AnalysisStatus.SUCCESS,
                        file_path=file_path,
                        confidence=selected_candidate.get('confidence', result.confidence),
                        method_used=AnalysisMethod.MUSICBRAINZ,
                        metadata=selected_candidate,
                        audio_properties=result.audio_properties,
                        processing_time=result.processing_time
                    )
                    
                    # Enregistrer la sélection manuelle
                    self.detailed_stats['manual_selections'].append({
                        'file_path': file_path,
                        'original': result.metadata,
                        'selected': selected_candidate
                    })
                    
                    return new_result
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur sélection manuelle: {e}")
        
        return result
    
    def _get_musicbrainz_candidates(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les candidats MusicBrainz pour un fichier
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            List[Dict]: Liste des candidats
        """
        try:
            # Extraire les métadonnées existantes
            metadata = self.processor._extract_existing_metadata(file_path)
            
            if metadata:
                # Effectuer une recherche MusicBrainz étendue
                musicbrainz_data = self.processor.musicbrainz_component.search_by_metadata(
                    metadata, limit=10  # Récupérer plus de résultats
                )
                
                if musicbrainz_data and 'results' in musicbrainz_data:
                    return musicbrainz_data['results']
        
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Erreur récupération candidats: {e}")
        
        return []
    
    def clear_cache(self):
        """Vide tous les caches"""
        try:
            # Cache du processeur unifié
            self.processor.clear_cache()
            
            # Cache profond
            if self.enable_deep_cache:
                self.cache_manager.clear_cache('deep_analysis')
            
            if self.status_callback:
                self.status_callback("🧹 Tous les caches ont été vidés")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur vidage cache: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erreur vidage cache: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques détaillées"""
        base_stats = self.processor.get_statistics()
        
        # Ajouter les statistiques avancées
        base_stats.update({
            'corrupted_files_count': len(self.detailed_stats['corrupted_files']),
            'manual_selections_count': len(self.detailed_stats['manual_selections']),
            'deep_cache_enabled': self.enable_deep_cache,
            'skip_corrupted_enabled': self.skip_corrupted_files,
            'manual_selection_enabled': self.enable_manual_selection
        })
        
        return base_stats
    
    def export_results(self, file_path: str, format_type: str = 'json'):
        """
        Exporte les résultats dans différents formats
        
        Args:
            file_path: Chemin du fichier d'export
            format_type: Format d'export ('json', 'csv', 'txt')
        """
        try:
            if format_type == 'json':
                self._export_json(file_path)
            elif format_type == 'csv':
                self._export_csv(file_path)
            elif format_type == 'txt':
                self._export_txt(file_path)
            
            if self.status_callback:
                self.status_callback(f"📄 Export {format_type.upper()} terminé: {file_path}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur export: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erreur export: {e}")
    
    def _export_json(self, file_path: str):
        """Exporte en JSON"""
        export_data = {
            'results': [result.to_dict() for result in self.current_results],
            'statistics': self.get_statistics(),
            'detailed_stats': self.detailed_stats
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _export_csv(self, file_path: str):
        """Exporte en CSV"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # En-têtes
            writer.writerow([
                'Fichier', 'Statut', 'Méthode', 'Confiance', 
                'Artiste', 'Titre', 'Album', 'Année', 'Durée'
            ])
            
            # Données
            for result in self.current_results:
                writer.writerow([
                    result.file_path,
                    result.status.value,
                    result.method_used.value if result.method_used else '',
                    result.confidence,
                    result.metadata.get('artist', ''),
                    result.metadata.get('title', ''),
                    result.metadata.get('album', ''),
                    result.metadata.get('year', ''),
                    result.metadata.get('duration', '')
                ])
    
    def _export_txt(self, file_path: str):
        """Exporte en TXT"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("RAPPORT D'ANALYSE MUSICALE\n")
            f.write("=" * 50 + "\n\n")
            
            # Statistiques
            stats = self.get_statistics()
            f.write("STATISTIQUES:\n")
            f.write(f"Total traité: {stats['total_processed']}\n")
            f.write(f"Taux de succès: {stats['success_rate']:.1%}\n")
            f.write(f"Fichiers corrompus: {stats['corrupted_files_count']}\n")
            f.write(f"Sélections manuelles: {stats['manual_selections_count']}\n\n")
            
            # Résultats détaillés
            f.write("RÉSULTATS DÉTAILLÉS:\n")
            f.write("-" * 30 + "\n")
            
            for result in self.current_results:
                f.write(f"\nFichier: {Path(result.file_path).name}\n")
                f.write(f"Statut: {result.status.value}\n")
                f.write(f"Méthode: {result.method_used.value if result.method_used else 'Aucune'}\n")
                f.write(f"Confiance: {result.confidence:.2f}\n")
                
                if result.metadata:
                    f.write("Métadonnées:\n")
                    for key, value in result.metadata.items():
                        f.write(f"  {key}: {value}\n")
                
                if result.errors:
                    f.write("Erreurs:\n")
                    for error in result.errors:
                        f.write(f"  - {error}\n")
                
                f.write("\n" + "-" * 30 + "\n")
