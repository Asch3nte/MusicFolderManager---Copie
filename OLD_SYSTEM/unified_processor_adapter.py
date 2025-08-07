#!/usr/bin/env python3
"""
Adaptateur Interface Utilisateur pour le Processeur Audio Unifié
Compatible avec l'interface existante de MusicFolderManager
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path

from unified_audio_processor import UnifiedAudioProcessor, AnalysisResult, AnalysisStatus, AnalysisMethod
from utils.file_utils import is_audio_file

class UnifiedProcessorAdapter:
    """
    Adaptateur pour intégrer le processeur unifié avec l'interface existante
    """
    
    def __init__(self, config_manager=None, logger=None):
        """
        Initialise l'adaptateur
        
        Args:
            config_manager: Gestionnaire de configuration existant
            logger: Logger existant
        """
        self.config = config_manager
        self.logger = logger
        
        # Récupérer la clé API depuis la configuration
        api_key = None
        if self.config:
            api_key = self.config.get('APIS', 'acoustid_api_key', fallback='')
        
        # Initialiser le processeur unifié
        self.processor = UnifiedAudioProcessor(api_key=api_key)
        
        # Callbacks pour l'interface
        self.progress_callback = None
        self.status_callback = None
        self.result_callback = None
        
        # État du traitement
        self.is_processing = False
        self.current_results = []
        self.processing_thread = None
    
    def set_callbacks(self, progress_callback: Callable = None, 
                     status_callback: Callable = None,
                     result_callback: Callable = None):
        """
        Configure les callbacks pour l'interface utilisateur
        
        Args:
            progress_callback: Fonction(current, total, result) pour la progression
            status_callback: Fonction(message) pour les messages de statut
            result_callback: Fonction(results) pour les résultats finaux
        """
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.result_callback = result_callback
    
    def configure_api_key(self, api_key: str):
        """Configure la clé API AcoustID"""
        self.processor.api_key = api_key
        if self.config:
            self.config.set('APIS', 'acoustid_api_key', api_key)
        
        if self.status_callback:
            self.status_callback("🔑 Clé API AcoustID configurée")
    
    def configure_thresholds(self, acousticid_threshold: float = None,
                           spectral_threshold: float = None,
                           musicbrainz_threshold: float = None):
        """Configure les seuils de confiance"""
        kwargs = {}
        if acousticid_threshold is not None:
            kwargs['acousticid_min_confidence'] = acousticid_threshold
        if spectral_threshold is not None:
            kwargs['spectral_similarity_threshold'] = spectral_threshold
        if musicbrainz_threshold is not None:
            kwargs['musicbrainz_min_confidence'] = musicbrainz_threshold
        
        if kwargs:
            self.processor.configure_thresholds(**kwargs)
            
            if self.status_callback:
                self.status_callback("⚙️ Seuils de confiance mis à jour")
    
    def scan_directory(self, directory: str) -> List[str]:
        """
        Scanne un répertoire pour trouver les fichiers audio
        
        Args:
            directory: Chemin du répertoire à scanner
            
        Returns:
            List[str]: Liste des fichiers audio trouvés
        """
        audio_files = []
        
        if self.status_callback:
            self.status_callback(f"🔍 Scan du répertoire: {directory}")
        
        try:
            # Utiliser os.walk comme dans l'ancienne interface (méthode éprouvée)
            import os
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        audio_files.append(file_path)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur lors du scan: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erreur de scan: {e}")
        
        if self.status_callback:
            self.status_callback(f"📁 {len(audio_files)} fichiers audio trouvés")
        
        return audio_files
    
    def process_files_async(self, file_paths: List[str], enable_methods: Dict[str, bool] = None):
        """
        Traite une liste de fichiers de manière asynchrone
        
        Args:
            file_paths: Liste des chemins de fichiers
            enable_methods: Dict des méthodes à activer/désactiver
        """
        if self.is_processing:
            if self.status_callback:
                self.status_callback("⚠️ Traitement déjà en cours")
            return
        
        # Configurer les méthodes à utiliser
        methods = self._configure_methods(enable_methods or {})
        
        # Lancer le traitement dans un thread séparé
        self.processing_thread = threading.Thread(
            target=self._process_files_worker,
            args=(file_paths, methods),
            daemon=True
        )
        self.processing_thread.start()
    
    def _configure_methods(self, enable_methods: Dict[str, bool]) -> List[AnalysisMethod]:
        """Configure les méthodes d'analyse à utiliser"""
        method_mapping = {
            'acousticid': AnalysisMethod.ACOUSTICID,
            'spectral': AnalysisMethod.SPECTRAL,
            'musicbrainz': AnalysisMethod.MUSICBRAINZ,
            'metadata': AnalysisMethod.METADATA_EXTRACTION
        }
        
        # Si aucune configuration spécifique, utiliser toutes les méthodes
        if not enable_methods:
            return list(AnalysisMethod)
        
        methods = []
        for method_name, enabled in enable_methods.items():
            if enabled and method_name in method_mapping:
                methods.append(method_mapping[method_name])
        
        return methods if methods else list(AnalysisMethod)
    
    def _process_files_worker(self, file_paths: List[str], methods: List[AnalysisMethod]):
        """Worker thread pour le traitement des fichiers"""
        self.is_processing = True
        self.current_results = []
        
        try:
            if self.status_callback:
                self.status_callback(f"🎵 Démarrage du traitement de {len(file_paths)} fichiers")
            
            def progress_update(current: int, total: int, result: AnalysisResult):
                self.current_results.append(result)
                
                if self.progress_callback:
                    self.progress_callback(current, total, result)
                
                if self.status_callback:
                    status_icon = self._get_status_icon(result.status)
                    method_icon = self._get_method_icon(result.method_used)
                    filename = Path(result.file_path).name
                    self.status_callback(f"{status_icon} {method_icon} {filename} ({current}/{total})")
            
            # Traitement batch
            results = self.processor.process_batch(file_paths, progress_callback=progress_update)
            
            if self.status_callback:
                stats = self.processor.get_statistics()
                self.status_callback(f"✅ Traitement terminé - Succès: {stats['success_rate']:.1%}")
            
            if self.result_callback:
                self.result_callback(results)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur durant le traitement: {e}")
            if self.status_callback:
                self.status_callback(f"💥 Erreur critique: {e}")
        
        finally:
            self.is_processing = False
    
    def _get_status_icon(self, status: AnalysisStatus) -> str:
        """Retourne l'icône correspondant au statut"""
        icons = {
            AnalysisStatus.SUCCESS: "✅",
            AnalysisStatus.PARTIAL_SUCCESS: "⚠️",
            AnalysisStatus.FAILED: "❌",
            AnalysisStatus.MANUAL_REVIEW: "🔍",
            AnalysisStatus.CACHED: "💾"
        }
        return icons.get(status, "❓")
    
    def _get_method_icon(self, method: Optional[AnalysisMethod]) -> str:
        """Retourne l'icône correspondant à la méthode"""
        if not method:
            return "❓"
        
        icons = {
            AnalysisMethod.ACOUSTICID: "🎧",
            AnalysisMethod.SPECTRAL: "📊", 
            AnalysisMethod.MUSICBRAINZ: "🎼",
            AnalysisMethod.METADATA_EXTRACTION: "🏷️"
        }
        return icons.get(method, "❓")
    
    def stop_processing(self):
        """Arrête le traitement en cours (si possible)"""
        if self.is_processing:
            self.is_processing = False
            if self.status_callback:
                self.status_callback("🛑 Arrêt du traitement demandé")
    
    def get_current_results(self) -> List[AnalysisResult]:
        """Retourne les résultats actuels"""
        return self.current_results.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du processeur"""
        return self.processor.get_statistics()
    
    def clear_cache(self):
        """Vide le cache"""
        self.processor.clear_cache()
        if self.status_callback:
            self.status_callback("🧹 Cache vidé")
    
    def export_results(self, file_path: str, format: str = 'json'):
        """
        Exporte les résultats vers un fichier
        
        Args:
            file_path: Chemin du fichier de sortie
            format: Format d'export ('json', 'csv', 'txt')
        """
        if not self.current_results:
            if self.status_callback:
                self.status_callback("⚠️ Aucun résultat à exporter")
            return
        
        try:
            if format.lower() == 'json':
                self._export_json(file_path)
            elif format.lower() == 'csv':
                self._export_csv(file_path)
            elif format.lower() == 'txt':
                self._export_txt(file_path)
            else:
                raise ValueError(f"Format non supporté: {format}")
            
            if self.status_callback:
                self.status_callback(f"📄 Résultats exportés vers: {file_path}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur export: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erreur export: {e}")
    
    def _export_json(self, file_path: str):
        """Exporte en JSON"""
        import json
        
        export_data = {
            'metadata': {
                'total_files': len(self.current_results),
                'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': self.processor.get_statistics()
            },
            'results': [result.to_dict() for result in self.current_results]
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
                'File Path', 'Status', 'Method', 'Confidence', 'Title', 'Artist', 
                'Album', 'Year', 'Processing Time', 'Errors'
            ])
            
            # Données
            for result in self.current_results:
                writer.writerow([
                    result.file_path,
                    result.status.value,
                    result.method_used.value if result.method_used else '',
                    result.confidence,
                    result.metadata.get('title', ''),
                    result.metadata.get('artist', ''),
                    result.metadata.get('album', ''),
                    result.metadata.get('year', ''),
                    result.processing_time,
                    '; '.join(result.errors)
                ])
    
    def _export_txt(self, file_path: str):
        """Exporte en TXT lisible"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("🎵 MusicFolderManager - Rapport d'Analyse\n")
            f.write("=" * 50 + "\n\n")
            
            # Statistiques
            stats = self.processor.get_statistics()
            f.write("📊 Statistiques:\n")
            f.write(f"   Total traité: {stats['total_processed']}\n")
            f.write(f"   Taux de succès: {stats['success_rate']:.1%}\n")
            f.write(f"   Cache: {stats['cache_hit_rate']:.1%}\n")
            f.write(f"   Temps moyen: {stats['average_processing_time']:.2f}s\n\n")
            
            # Résultats détaillés
            f.write("📁 Résultats détaillés:\n")
            f.write("-" * 30 + "\n")
            
            for i, result in enumerate(self.current_results, 1):
                f.write(f"\n{i}. {Path(result.file_path).name}\n")
                f.write(f"   Statut: {result.status.value}\n")
                f.write(f"   Méthode: {result.method_used.value if result.method_used else 'Aucune'}\n")
                f.write(f"   Confiance: {result.confidence:.2f}\n")
                
                if result.metadata:
                    f.write("   Métadonnées:\n")
                    for key, value in result.metadata.items():
                        f.write(f"     {key}: {value}\n")
                
                if result.errors:
                    f.write("   Erreurs:\n")
                    for error in result.errors:
                        f.write(f"     - {error}\n")


# Interface graphique de test simple
class UnifiedProcessorGUI:
    """Interface graphique simple pour tester le processeur unifié"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎵 Processeur Audio Unifié - Test")
        self.root.geometry("800x600")
        
        # Adaptateur
        self.adapter = UnifiedProcessorAdapter()
        self.adapter.set_callbacks(
            progress_callback=self.update_progress,
            status_callback=self.update_status,
            result_callback=self.show_results
        )
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Configuration
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(config_frame, text="Clé API AcoustID:").pack(anchor='w')
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=50)
        api_entry.pack(fill='x', pady=2)
        
        ttk.Button(config_frame, text="Configurer API", 
                  command=self.configure_api).pack(anchor='w', pady=2)
        
        # Sélection de fichiers
        files_frame = ttk.LabelFrame(self.root, text="Fichiers", padding=10)
        files_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Button(files_frame, text="Sélectionner Répertoire", 
                  command=self.select_directory).pack(anchor='w', pady=2)
        
        # Liste des fichiers
        self.files_listbox = tk.Listbox(files_frame, height=10)
        self.files_listbox.pack(fill='both', expand=True, pady=5)
        
        # Contrôles
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(controls_frame, text="🎵 Analyser", 
                  command=self.start_analysis).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="🛑 Arrêter", 
                  command=self.stop_analysis).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="🧹 Vider Cache", 
                  command=self.clear_cache).pack(side='left', padx=5)
        
        # Progression
        self.progress_var = tk.StringVar(value="Prêt")
        ttk.Label(self.root, textvariable=self.progress_var).pack(anchor='w', padx=10)
        
        self.progress_bar = ttk.Progressbar(self.root, mode='determinate')
        self.progress_bar.pack(fill='x', padx=10, pady=5)
        
        # Statut
        self.status_text = tk.Text(self.root, height=8)
        self.status_text.pack(fill='x', padx=10, pady=5)
    
    def configure_api(self):
        api_key = self.api_key_var.get().strip()
        if api_key:
            self.adapter.configure_api_key(api_key)
        else:
            messagebox.showwarning("Attention", "Veuillez entrer une clé API")
    
    def select_directory(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="Sélectionner le répertoire musical")
        if directory:
            files = self.adapter.scan_directory(directory)
            self.files_listbox.delete(0, tk.END)
            for file_path in files:
                self.files_listbox.insert(tk.END, Path(file_path).name)
            self.current_files = files
    
    def start_analysis(self):
        if hasattr(self, 'current_files') and self.current_files:
            self.progress_bar['maximum'] = len(self.current_files)
            self.adapter.process_files_async(self.current_files)
        else:
            messagebox.showinfo("Info", "Veuillez d'abord sélectionner un répertoire")
    
    def stop_analysis(self):
        self.adapter.stop_processing()
    
    def clear_cache(self):
        self.adapter.clear_cache()
    
    def update_progress(self, current: int, total: int, result: AnalysisResult):
        self.progress_var.set(f"Progression: {current}/{total}")
        self.progress_bar['value'] = current
        self.root.update_idletasks()
    
    def update_status(self, message: str):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def show_results(self, results: List[AnalysisResult]):
        stats = self.adapter.get_statistics()
        summary = f"\n✅ Analyse terminée!\n"
        summary += f"📊 {stats['total_processed']} fichiers traités\n"
        summary += f"🎯 Taux de succès: {stats['success_rate']:.1%}\n"
        summary += f"⏱️ Temps moyen: {stats['average_processing_time']:.2f}s\n"
        
        self.status_text.insert(tk.END, summary)
        self.status_text.see(tk.END)
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # Lancer l'interface de test
    app = UnifiedProcessorGUI()
    app.run()
