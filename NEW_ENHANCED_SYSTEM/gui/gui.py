"""
Interface utilisateur complète pour Enhanced Music Manager
Inclut toutes les fonctionnalités manquantes et une interface moderne
"""

print("🔍 Debug: Début du module complete_music_gui.py")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

print("🔍 Debug: Imports de base OK")

# Imports du système enhanced (avec fallback)
try:
    from core.enhanced_unified_adapter import EnhancedUnifiedProcessorAdapter as EnhancedUnifiedAdapter
    from core.unified_audio_processor import AnalysisResult, AnalysisStatus, AnalysisMethod
    ENHANCED_CORE_AVAILABLE = True
    print("🔍 Debug: Import du core enhanced OK")
except ImportError as e:
    print(f"🔍 Debug: Import du core enhanced échoué: {e}")
    # Fallback - utiliser des classes simulées
    ENHANCED_CORE_AVAILABLE = False
    # Fallback - utiliser des classes simulées
    ENHANCED_CORE_AVAILABLE = False
    
    class MockAnalysisStatus:
        SUCCESS = "success"
        PARTIAL_SUCCESS = "partial_success"
        FAILED = "failed"
        MANUAL_REVIEW = "manual_review"
        CACHED = "cached"
    
    class MockAnalysisMethod:
        ACOUSTICID = "acousticid"
        SPECTRAL = "spectral"
        MUSICBRAINZ = "musicbrainz"
        METADATA_EXTRACTION = "metadata"
    
    class MockAnalysisResult:
        def __init__(self, file_path, status="pending"):
            self.file_path = file_path
            self.status = status
            self.method_used = None
            self.confidence = 0.0
            self.processing_time = 0.0
            self.cache_hit = False
            self.metadata = {}
            self.audio_properties = {}
            self.errors = []
            self.suggestions = []
    
    class MockEnhancedUnifiedAdapter:
        def __init__(self, **kwargs):
            self.is_processing = False
            self.selected_files = []
            
        def configure_api_key(self, key): pass
        def configure_processing_options(self, **kwargs): pass
        def configure_thresholds(self, **kwargs): pass
        def scan_directory(self, directory): 
            import os
            from pathlib import Path
            audio_ext = {'.mp3', '.flac', '.wav', '.m4a', '.ogg', '.wma', '.aac', '.opus'}
            files = []
            try:
                for root, dirs, filenames in os.walk(directory):
                    for filename in filenames:
                        if Path(filename).suffix.lower() in audio_ext:
                            file_path = os.path.join(root, filename)
                            # Vérification basique de l'existence et de la taille
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
                                files.append(file_path)
                print(f"📁 Mock Scanner: {len(files)} fichiers audio trouvés")
            except Exception as e:
                print(f"❌ Erreur scan: {e}")
            return files
        def set_file_selection(self, file_path, selected): pass
        def get_selected_files(self): return self.selected_files
        def process_files_async(self, files, methods): pass
        def stop_processing(self): pass
        def clear_cache(self): pass
        def export_results(self, file_path, format_type): pass
        def get_statistics(self): 
            return {
                'total_processed': 0, 'success_rate': 0.0, 'cache_hit_rate': 0.0,
                'average_processing_time': 0.0, 'total_processing_time': 0.0,
                'acousticid_successes': 0, 'spectral_successes': 0, 'musicbrainz_successes': 0,
                'manual_reviews': 0, 'errors': 0, 'corrupted_files_count': 0, 'manual_selections_count': 0
            }
    
    # Utiliser les classes mock
    AnalysisStatus = MockAnalysisStatus()
    AnalysisMethod = MockAnalysisMethod()
    AnalysisResult = MockAnalysisResult
    EnhancedUnifiedAdapter = MockEnhancedUnifiedAdapter

print("🔍 Debug: Configuration des imports terminée")

class CompleteMusicManagerGUI:
    """Interface utilisateur complète avec toutes les fonctionnalités"""
    
    def __init__(self):
        """Initialise l'interface utilisateur complète"""
        print("🎵 Initialisation de l'interface Enhanced Music Manager...")
        
        # Interface graphique principale
        self.root = tk.Tk()
        self.root.title("🎵 Enhanced Music Manager - Interface Complète")
        self.root.geometry("1200x750")  # Plus large pour plus d'espace
        self.root.minsize(1000, 650)
        
        # Variables de l'interface
        self.api_key = tk.StringVar()
        self.source_directory = tk.StringVar()
        
        # Seuils de confiance
        self.acoustid_threshold = tk.DoubleVar(value=0.85)
        self.musicbrainz_threshold = tk.DoubleVar(value=0.70)
        self.spectral_threshold = tk.DoubleVar(value=0.70)
        
        # Options avancées
        self.skip_corrupted = tk.BooleanVar(value=False)  # Désactivé par défaut pour éviter les faux positifs
        self.enable_manual_selection = tk.BooleanVar(value=True)
        self.enable_deep_cache = tk.BooleanVar(value=True)
        
        # Méthodes d'analyse
        self.enable_acousticid = tk.BooleanVar(value=True)
        self.enable_spectral = tk.BooleanVar(value=True)
        self.enable_musicbrainz = tk.BooleanVar(value=True)
        self.enable_metadata = tk.BooleanVar(value=True)
        
        # Variables pour les labels des seuils
        self.acoustid_label = tk.StringVar()
        self.musicbrainz_label = tk.StringVar()
        self.spectral_label = tk.StringVar()
        
        # État de sélection des fichiers
        self.file_checkboxes = {}  # item_id -> BooleanVar
        self.file_paths_map = {}   # item_id -> file_path
        self.current_files = []
        self.current_results = []
        
        # Configuration
        self.config_file = Path("config/ui_settings.json")
        
        # Charger les paramètres sauvegardés
        self.load_settings()
        
        # Configurer les callbacks de sauvegarde automatique
        self.setup_auto_save()
        
        self.setup_ui()
        
        # Initialiser l'adaptateur APRÈS setup_ui pour avoir toutes les méthodes disponibles
        print("🔧 Initialisation de l'adaptateur...")
        if ENHANCED_CORE_AVAILABLE:
            self.adapter = EnhancedUnifiedAdapter()
            # Configurer les callbacks
            self.adapter.set_callbacks(
                progress_callback=self.on_progress_update,
                status_callback=self.on_status_update,
                result_callback=self.on_results_ready,
                manual_selection_callback=self.on_manual_selection_request
            )
        else:
            self.adapter = EnhancedUnifiedAdapter(
                api_key=self.api_key.get(),
                progress_callback=self.on_progress_update,
                status_callback=self.on_status_update,
                results_callback=self.on_results_ready,
                manual_selection_callback=self.on_manual_selection_request
            )
        
        # Mettre à jour les labels après la création de l'interface
        self.update_threshold_labels()
        
        # Configurer la fermeture propre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        """Configure l'interface utilisateur complète"""
        
        # === ONGLETS PRINCIPAUX ===
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Onglet Configuration
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ Configuration")
        self.setup_config_tab(config_frame)
        
        # Onglet Analyse
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="🔍 Analyse")
        self.setup_analysis_tab(analysis_frame)
        
        # Onglet Résultats
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="📊 Résultats")
        self.setup_results_tab(results_frame)
        
        # Onglet Options Avancées
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="🔧 Options Avancées")
        self.setup_advanced_tab(advanced_frame)
        
        # Onglet Statistiques
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📈 Statistiques")
        self.setup_stats_tab(stats_frame)
    
    def setup_config_tab(self, parent):
        """Onglet de configuration"""
        
        # === CONFIGURATION API ===
        api_group = ttk.LabelFrame(parent, text="🔑 Configuration API", padding=15)
        api_group.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(api_group, text="Clé API AcoustID:").pack(anchor='w')
        api_entry = ttk.Entry(api_group, textvariable=self.api_key, width=60, show='*')
        api_entry.pack(fill='x', pady=5)
        
        ttk.Button(api_group, text="💾 Configurer API", 
                  command=self.configure_api_key).pack(anchor='w')
        
        # === SÉLECTION DE RÉPERTOIRE ===
        dir_group = ttk.LabelFrame(parent, text="📁 Répertoire Source", padding=15)
        dir_group.pack(fill='x', padx=10, pady=10)
        
        dir_frame = ttk.Frame(dir_group)
        dir_frame.pack(fill='x')
        
        ttk.Entry(dir_frame, textvariable=self.source_directory, 
                 state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(dir_frame, text="📂 Parcourir", 
                  command=self.select_source_directory).pack(side='right', padx=(5,0))
        
        # === SEUILS DE CONFIANCE ===
        thresholds_group = ttk.LabelFrame(parent, text="🎯 Seuils de Confiance", padding=15)
        thresholds_group.pack(fill='x', padx=10, pady=10)
        
        # AcoustID
        self.acoustid_label.set(f"AcoustID (recommandé: 0.85): {self.acoustid_threshold.get():.2f}")
        ttk.Label(thresholds_group, textvariable=self.acoustid_label).pack(anchor='w')
        acoustid_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, variable=self.acoustid_threshold,
                 orient='horizontal', command=self.on_acoustid_change)
        acoustid_scale.pack(fill='x', pady=2)
        
        # Spectral
        self.spectral_label.set(f"Analyse Spectrale (recommandé: 0.70): {self.spectral_threshold.get():.2f}")
        ttk.Label(thresholds_group, textvariable=self.spectral_label).pack(anchor='w')
        spectral_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, variable=self.spectral_threshold,
                 orient='horizontal', command=self.on_spectral_change)
        spectral_scale.pack(fill='x', pady=2)
        
        # MusicBrainz
        self.musicbrainz_label.set(f"MusicBrainz (recommandé: 0.70): {self.musicbrainz_threshold.get():.2f}")
        ttk.Label(thresholds_group, textvariable=self.musicbrainz_label).pack(anchor='w')
        musicbrainz_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, variable=self.musicbrainz_threshold,
                 orient='horizontal', command=self.on_musicbrainz_change)
        musicbrainz_scale.pack(fill='x', pady=2)
    
    def setup_analysis_tab(self, parent):
        """Onglet d'analyse avec cases à cocher"""
        
        # === SÉLECTION DE FICHIERS ===
        files_group = ttk.LabelFrame(parent, text="🎵 Fichiers à Analyser", padding=15)
        files_group.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Boutons de contrôle
        controls_frame = ttk.Frame(files_group)
        controls_frame.pack(fill='x', pady=(0,10))
        
        # Ligne 1: Scan et sélection
        controls_row1 = ttk.Frame(controls_frame)
        controls_row1.pack(fill='x', pady=2)
        
        ttk.Button(controls_row1, text="🔍 Scanner Répertoire", 
                  command=self.scan_directory).pack(side='left', padx=5)
        ttk.Button(controls_row1, text="☑️ Tout Sélectionner", 
                  command=self.select_all_files).pack(side='left', padx=5)
        ttk.Button(controls_row1, text="☐ Tout Désélectionner", 
                  command=self.clear_all_selection).pack(side='left', padx=5)
        
        # Ligne 2: Traitement
        controls_row2 = ttk.Frame(controls_frame)
        controls_row2.pack(fill='x', pady=2)
        
        ttk.Button(controls_row2, text="🎵 Analyser Sélectionnés", 
                  command=self.start_analysis).pack(side='left', padx=5)
        ttk.Button(controls_row2, text="🛑 Arrêter", 
                  command=self.stop_analysis).pack(side='left', padx=5)
        ttk.Button(controls_row2, text="🧹 Vider Cache", 
                  command=self.clear_cache).pack(side='right', padx=5)
        
        # Liste des fichiers avec checkboxes
        files_list_frame = ttk.Frame(files_group)
        files_list_frame.pack(fill='both', expand=True)
        
        # Treeview pour afficher les fichiers avec cases à cocher
        columns = ('Sélection', 'Nom', 'Taille', 'Statut')
        self.files_tree = ttk.Treeview(files_list_frame, columns=columns, show='headings', height=12)
        
        # Configuration des colonnes
        self.files_tree.heading('Sélection', text='☑️')
        self.files_tree.column('Sélection', width=50, minwidth=50)
        
        for col in columns[1:]:
            self.files_tree.heading(col, text=col)
            self.files_tree.column(col, width=150)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(files_list_frame, orient='vertical', command=self.files_tree.yview)
        h_scroll = ttk.Scrollbar(files_list_frame, orient='horizontal', command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Bind pour les clicks sur les cases à cocher
        self.files_tree.bind('<Button-1>', self.on_file_click)
        
        # Pack treeview et scrollbars
        self.files_tree.pack(side='left', fill='both', expand=True)
        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        
        # === PROGRESSION ===
        progress_group = ttk.LabelFrame(parent, text="📊 Progression", padding=15)
        progress_group.pack(fill='x', padx=10, pady=10)
        
        # Barre de progression
        self.progress_var = tk.StringVar(value="Prêt à analyser")
        ttk.Label(progress_group, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(progress_group, mode='determinate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Zone de statut avec défilement
        status_frame = ttk.Frame(progress_group)
        status_frame.pack(fill='x', pady=5)
        
        self.status_text = tk.Text(status_frame, height=6, wrap='word')
        status_scroll = ttk.Scrollbar(status_frame, orient='vertical', command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scroll.set)
        
        self.status_text.pack(side='left', fill='both', expand=True)
        status_scroll.pack(side='right', fill='y')
    
    def setup_results_tab(self, parent):
        """Onglet des résultats"""
        
        # === RÉSULTATS DÉTAILLÉS ===
        results_group = ttk.LabelFrame(parent, text="🎯 Résultats d'Analyse", padding=15)
        results_group.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Boutons d'export
        export_frame = ttk.Frame(results_group)
        export_frame.pack(fill='x', pady=(0,10))
        
        ttk.Button(export_frame, text="📄 Exporter JSON", 
                  command=lambda: self.export_results('json')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📊 Exporter CSV", 
                  command=lambda: self.export_results('csv')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📝 Exporter TXT", 
                  command=lambda: self.export_results('txt')).pack(side='left', padx=5)
        
        # Treeview des résultats
        result_columns = ('Fichier', 'Statut', 'Méthode', 'Confiance', 'Artiste', 'Titre', 'Album')
        self.results_tree = ttk.Treeview(results_group, columns=result_columns, show='headings', height=15)
        
        for col in result_columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120)
        
        # Scrollbars pour résultats
        results_v_scroll = ttk.Scrollbar(results_group, orient='vertical', command=self.results_tree.yview)
        results_h_scroll = ttk.Scrollbar(results_group, orient='horizontal', command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=results_v_scroll.set, xscrollcommand=results_h_scroll.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_v_scroll.pack(side='right', fill='y')
        results_h_scroll.pack(side='bottom', fill='x')
        
        # Double-clic pour voir les détails
        self.results_tree.bind('<Double-1>', self.show_result_details)
    
    def setup_advanced_tab(self, parent):
        """Onglet des options avancées"""
        
        # === OPTIONS DE TRAITEMENT ===
        processing_group = ttk.LabelFrame(parent, text="🔧 Options de Traitement", padding=15)
        processing_group.pack(fill='x', padx=10, pady=10)
        
        # Fichiers corrompus
        ttk.Checkbutton(processing_group, text="Ignorer les fichiers corrompus", 
                       variable=self.skip_corrupted, 
                       command=self.update_processing_options).pack(anchor='w', pady=5)
        
        # Sélection manuelle
        ttk.Checkbutton(processing_group, text="Activer la sélection manuelle MusicBrainz", 
                       variable=self.enable_manual_selection,
                       command=self.update_processing_options).pack(anchor='w', pady=5)
        
        # Cache profond
        ttk.Checkbutton(processing_group, text="Activer le cache profond", 
                       variable=self.enable_deep_cache,
                       command=self.update_processing_options).pack(anchor='w', pady=5)
        
        # === MÉTHODES D'ANALYSE ===
        methods_group = ttk.LabelFrame(parent, text="🎯 Méthodes d'Analyse", padding=15)
        methods_group.pack(fill='x', padx=10, pady=10)
        
        ttk.Checkbutton(methods_group, text="🎧 AcoustID (Empreinte acoustique)", 
                       variable=self.enable_acousticid).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(methods_group, text="📊 Analyse Spectrale", 
                       variable=self.enable_spectral).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(methods_group, text="🎼 MusicBrainz (Base de données)", 
                       variable=self.enable_musicbrainz).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(methods_group, text="🏷️ Extraction Métadonnées", 
                       variable=self.enable_metadata).pack(anchor='w', pady=2)
        
        # === GESTION DU CACHE ===
        cache_group = ttk.LabelFrame(parent, text="💾 Gestion du Cache", padding=15)
        cache_group.pack(fill='x', padx=10, pady=10)
        
        cache_buttons = ttk.Frame(cache_group)
        cache_buttons.pack(fill='x')
        
        ttk.Button(cache_buttons, text="🧹 Vider Cache Unifié", 
                  command=self.clear_cache).pack(side='left', padx=5)
        ttk.Button(cache_buttons, text="📊 Statistiques Cache", 
                  command=self.show_cache_stats).pack(side='left', padx=5)
        ttk.Button(cache_buttons, text="🔧 Optimiser Cache", 
                  command=self.optimize_cache).pack(side='left', padx=5)
    
    def setup_stats_tab(self, parent):
        """Onglet des statistiques"""
        
        # === STATISTIQUES GLOBALES ===
        stats_group = ttk.LabelFrame(parent, text="📈 Statistiques de Session", padding=15)
        stats_group.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Zone de texte pour les statistiques
        self.stats_text = tk.Text(stats_group, font=('Consolas', 11), wrap='word')
        stats_scroll = ttk.Scrollbar(stats_group, orient='vertical', command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scroll.set)
        
        self.stats_text.pack(side='left', fill='both', expand=True)
        stats_scroll.pack(side='right', fill='y')
        
        # Bouton pour rafraîchir les stats
        ttk.Button(stats_group, text="🔄 Rafraîchir Statistiques", 
                  command=self.update_statistics).pack(anchor='w', pady=10)
    
    # === MÉTHODES DE CALLBACK ===
    
    def configure_api_key(self):
        """Configure la clé API"""
        api_key = self.api_key.get().strip()
        if api_key:
            self.adapter.configure_api_key(api_key)
            messagebox.showinfo("✅ Succès", "Clé API configurée avec succès !")
        else:
            messagebox.showwarning("⚠️ Attention", "Veuillez entrer une clé API valide")
    
    def update_processing_options(self):
        """Met à jour les options de traitement avancées"""
        self.adapter.configure_processing_options(
            skip_corrupted=self.skip_corrupted.get(),
            enable_manual_selection=self.enable_manual_selection.get(),
            enable_deep_cache=self.enable_deep_cache.get()
        )
    
    def on_acoustid_change(self, value):
        """Callback pour le changement du seuil AcoustID"""
        val = float(value)
        self.acoustid_label.set(f"AcoustID (recommandé: 0.85): {val:.2f}")
        self.adapter.configure_thresholds(acousticid_threshold=val)
    
    def on_musicbrainz_change(self, value):
        """Callback pour le changement du seuil MusicBrainz"""
        val = float(value)
        self.musicbrainz_label.set(f"MusicBrainz (recommandé: 0.70): {val:.2f}")
        self.adapter.configure_thresholds(musicbrainz_threshold=val)
    
    def on_spectral_change(self, value):
        """Callback pour le changement du seuil Spectral"""
        val = float(value)
        self.spectral_label.set(f"Analyse Spectrale (recommandé: 0.70): {val:.2f}")
        self.adapter.configure_thresholds(spectral_threshold=val)
    
    def select_source_directory(self):
        """Sélectionne le répertoire source"""
        directory = filedialog.askdirectory(title="Sélectionner le répertoire musical")
        if directory:
            self.source_directory.set(directory)
    
    def scan_directory(self):
        """Scanne le répertoire pour trouver les fichiers audio"""
        directory = self.source_directory.get()
        if not directory:
            messagebox.showwarning("⚠️ Attention", "Veuillez d'abord sélectionner un répertoire")
            return
        
        # Scanner dans un thread séparé
        def scan_worker():
            files = self.adapter.scan_directory(directory)
            # Mettre à jour l'interface dans le thread principal
            self.root.after(0, lambda: self.populate_files_list(files))
        
        threading.Thread(target=scan_worker, daemon=True).start()
    
    def populate_files_list(self, files: List[str]):
        """Remplit la liste des fichiers avec cases à cocher"""
        # Vider la liste actuelle
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Vider les mappings
        self.file_paths_map.clear()
        self.file_checkboxes.clear()
        
        self.current_files = files
        
        # Ajouter les nouveaux fichiers
        for file_path in files:
            file_path_obj = Path(file_path)
            try:
                file_size = file_path_obj.stat().st_size
                size_str = f"{file_size / 1024 / 1024:.1f} MB"
            except:
                size_str = "Inconnu"
            
            # Créer une variable pour la case à cocher
            checkbox_var = tk.BooleanVar(value=True)  # Sélectionné par défaut
            
            item = self.files_tree.insert('', 'end', values=(
                '☑️',  # Case cochée par défaut
                file_path_obj.name,
                size_str,
                'En attente'
            ))
            
            # Stocker les mappings
            self.file_paths_map[item] = file_path
            self.file_checkboxes[item] = checkbox_var
            
            # Ajouter à la sélection de l'adaptateur
            self.adapter.set_file_selection(file_path, True)
        
        # Afficher un résumé
        if files:
            self.on_status_update(f"📁 {len(files)} fichiers audio trouvés et sélectionnés")
        else:
            self.on_status_update("⚠️ Aucun fichier audio trouvé dans le répertoire")
    
    def on_file_click(self, event):
        """Gère les clics sur les cases à cocher des fichiers"""
        # Déterminer où l'utilisateur a cliqué
        item = self.files_tree.identify_row(event.y)
        column = self.files_tree.identify_column(event.x)
        
        # Si clic sur la colonne de sélection
        if item and column == '#1':  # Première colonne (Sélection)
            self.toggle_file_selection(item)
    
    def toggle_file_selection(self, item):
        """Bascule la sélection d'un fichier"""
        if item in self.file_checkboxes:
            checkbox_var = self.file_checkboxes[item]
            file_path = self.file_paths_map[item]
            
            # Basculer l'état
            new_state = not checkbox_var.get()
            checkbox_var.set(new_state)
            
            # Mettre à jour l'affichage
            current_values = list(self.files_tree.item(item)['values'])
            current_values[0] = '☑️' if new_state else '☐'
            self.files_tree.item(item, values=current_values)
            
            # Mettre à jour la sélection dans l'adaptateur
            self.adapter.set_file_selection(file_path, new_state)
    
    def select_all_files(self):
        """Sélectionne tous les fichiers"""
        for item in self.files_tree.get_children():
            if item in self.file_checkboxes:
                checkbox_var = self.file_checkboxes[item]
                file_path = self.file_paths_map[item]
                
                checkbox_var.set(True)
                
                # Mettre à jour l'affichage
                current_values = list(self.files_tree.item(item)['values'])
                current_values[0] = '☑️'
                self.files_tree.item(item, values=current_values)
                
                # Mettre à jour la sélection dans l'adaptateur
                self.adapter.set_file_selection(file_path, True)
        
        self.on_status_update("☑️ Tous les fichiers sélectionnés")
    
    def clear_all_selection(self):
        """Désélectionne tous les fichiers"""
        for item in self.files_tree.get_children():
            if item in self.file_checkboxes:
                checkbox_var = self.file_checkboxes[item]
                file_path = self.file_paths_map[item]
                
                checkbox_var.set(False)
                
                # Mettre à jour l'affichage
                current_values = list(self.files_tree.item(item)['values'])
                current_values[0] = '☐'
                self.files_tree.item(item, values=current_values)
                
                # Mettre à jour la sélection dans l'adaptateur
                self.adapter.set_file_selection(file_path, False)
        
        self.on_status_update("☐ Tous les fichiers désélectionnés")
    
    def start_analysis(self):
        """Démarre l'analyse des fichiers sélectionnés"""
        # Vérifications préliminaires
        if not self.source_directory.get():
            messagebox.showwarning("⚠️ Attention", "Veuillez d'abord sélectionner un répertoire source")
            return
        
        if not self.api_key.get().strip():
            messagebox.showwarning("⚠️ Attention", "Veuillez configurer votre clé API AcoustID")
            return
        
        # Obtenir les fichiers sélectionnés
        selected_files = self.adapter.get_selected_files()
        
        if not selected_files:
            messagebox.showwarning("⚠️ Attention", "Aucun fichier sélectionné pour l'analyse")
            return
        
        # Configurer la progression
        self.progress_bar['maximum'] = len(selected_files)
        self.progress_bar['value'] = 0
        
        # Vider les résultats précédents
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Configuration des méthodes
        enable_methods = {
            'acousticid': self.enable_acousticid.get(),
            'spectral': self.enable_spectral.get(),
            'musicbrainz': self.enable_musicbrainz.get(),
            'metadata': self.enable_metadata.get()
        }
        
        # Messages de début
        self.on_status_update(f"🚀 Début de l'analyse de {len(selected_files)} fichiers sélectionnés...")
        self.on_status_update(f"🎯 Ordre d'analyse: 1️⃣ AcoustID → 2️⃣ Spectral → 3️⃣ MusicBrainz")
        self.on_status_update(f"🎯 Seuils: AcoustID={self.acoustid_threshold.get():.2f}, Spectral={self.spectral_threshold.get():.2f}, MusicBrainz={self.musicbrainz_threshold.get():.2f}")
        
        # Démarrer l'analyse
        self.adapter.process_files_async(selected_files, enable_methods)
    
    def stop_analysis(self):
        """Arrête l'analyse en cours"""
        self.adapter.stop_processing()
    
    def clear_cache(self):
        """Vide le cache"""
        self.adapter.clear_cache()
    
    def show_cache_stats(self):
        """Affiche les statistiques du cache"""
        # TODO: Implémenter l'affichage des stats cache
        messagebox.showinfo("📊 Cache", "Statistiques du cache à implémenter")
    
    def optimize_cache(self):
        """Optimise le cache"""
        # TODO: Implémenter l'optimisation du cache
        messagebox.showinfo("🔧 Cache", "Optimisation du cache à implémenter")
    
    def on_manual_selection_request(self, file_path: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Callback pour la sélection manuelle des résultats MusicBrainz"""
        if not candidates or len(candidates) <= 1:
            return None
        
        # Créer une fenêtre de sélection
        selection_window = ManualSelectionDialog(self.root, file_path, candidates)
        return selection_window.show()
    
    def on_progress_update(self, current: int, total: int, result):
        """Callback de progression"""
        # Mettre à jour la barre de progression
        self.progress_bar['value'] = current
        self.progress_var.set(f"Progression: {current}/{total} fichiers")
        
        # Mettre à jour le statut du fichier dans la liste
        filename = Path(result.file_path).name
        for item in self.files_tree.get_children():
            if item in self.file_paths_map:
                stored_path = self.file_paths_map[item]
                if Path(stored_path).name == filename:
                    status_icon = self.get_status_icon(result.status)
                    current_values = list(self.files_tree.item(item)['values'])
                    current_values[3] = f"{status_icon} {result.status.value}"
                    self.files_tree.item(item, values=current_values)
                    break
        
        # Ajouter aux résultats
        self.add_result_to_tree(result)
    
    def on_status_update(self, message: str):
        """Callback de statut"""
        self.status_text.insert('end', f"{message}\n")
        self.status_text.see('end')
        self.root.update_idletasks()
    
    def on_results_ready(self, results: List):
        """Callback des résultats finaux"""
        self.current_results = results
        
        # Afficher un résumé
        success_count = sum(1 for r in results if r.status == AnalysisStatus.SUCCESS)
        total_count = len(results)
        
        summary = f"\n✅ Analyse terminée !\n"
        summary += f"📊 Succès: {success_count}/{total_count} ({success_count/total_count:.1%})\n"
        
        self.status_text.insert('end', summary)
        self.status_text.see('end')
        
        # Mettre à jour les statistiques
        self.update_statistics()
        
        messagebox.showinfo("🎉 Terminé", 
            f"Analyse terminée !\nSuccès: {success_count}/{total_count}")
    
    def add_result_to_tree(self, result):
        """Ajoute un résultat à l'arbre des résultats"""
        status_icon = self.get_status_icon(result.status)
        method_icon = self.get_method_icon(result.method_used)
        
        self.results_tree.insert('', 'end', values=(
            Path(result.file_path).name,
            f"{status_icon} {result.status.value}",
            f"{method_icon} {result.method_used.value if result.method_used else 'Aucune'}",
            f"{result.confidence:.2f}",
            result.metadata.get('artist', ''),
            result.metadata.get('title', ''),
            result.metadata.get('album', '')
        ))
    
    def get_status_icon(self, status) -> str:
        """Retourne l'icône du statut"""
        icons = {
            AnalysisStatus.SUCCESS: "✅",
            AnalysisStatus.PARTIAL_SUCCESS: "⚠️",
            AnalysisStatus.FAILED: "❌",
            AnalysisStatus.MANUAL_REVIEW: "🔍",
            AnalysisStatus.CACHED: "💾"
        }
        return icons.get(status, "❓")
    
    def get_method_icon(self, method) -> str:
        """Retourne l'icône de la méthode"""
        if not method:
            return "❓"
        
        icons = {
            AnalysisMethod.ACOUSTICID: "🎧",
            AnalysisMethod.SPECTRAL: "📊",
            AnalysisMethod.MUSICBRAINZ: "🎼",
            AnalysisMethod.METADATA_EXTRACTION: "🏷️"
        }
        return icons.get(method, "❓")
    
    def show_result_details(self, event):
        """Affiche les détails d'un résultat"""
        selection = self.results_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.results_tree.item(item)['values']
        
        # Trouver le résultat correspondant
        filename = values[0]
        result = next((r for r in self.current_results if Path(r.file_path).name == filename), None)
        
        if result:
            self.show_detailed_result_window(result)
    
    def show_detailed_result_window(self, result):
        """Affiche une fenêtre détaillée pour un résultat"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"🔍 Détails - {Path(result.file_path).name}")
        detail_window.geometry("600x500")
        
        # Zone de texte avec les détails
        text_widget = tk.Text(detail_window, wrap='word', font=('Consolas', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Formater les détails
        details = f"📁 Fichier: {result.file_path}\n\n"
        details += f"📊 Statut: {result.status.value}\n"
        details += f"🎯 Méthode: {result.method_used.value if result.method_used else 'Aucune'}\n"
        details += f"📈 Confiance: {result.confidence:.2f}\n"
        details += f"⏱️ Temps de traitement: {result.processing_time:.2f}s\n"
        details += f"💾 Cache: {'Oui' if result.cache_hit else 'Non'}\n\n"
        
        if result.metadata:
            details += "🎵 Métadonnées:\n"
            for key, value in result.metadata.items():
                details += f"   {key}: {value}\n"
            details += "\n"
        
        if result.audio_properties:
            details += "📀 Propriétés Audio:\n"
            for key, value in result.audio_properties.items():
                details += f"   {key}: {value}\n"
            details += "\n"
        
        if result.errors:
            details += "❌ Erreurs:\n"
            for error in result.errors:
                details += f"   • {error}\n"
            details += "\n"
        
        if result.suggestions:
            details += "💡 Suggestions:\n"
            for suggestion in result.suggestions:
                details += f"   • {suggestion}\n"
        
        text_widget.insert('1.0', details)
        text_widget.config(state='disabled')
    
    def export_results(self, format_type: str):
        """Exporte les résultats"""
        if not self.current_results:
            messagebox.showwarning("⚠️ Attention", "Aucun résultat à exporter")
            return
        
        # Sélectionner le fichier de destination
        file_types = {
            'json': [("Fichiers JSON", "*.json")],
            'csv': [("Fichiers CSV", "*.csv")],
            'txt': [("Fichiers Texte", "*.txt")]
        }
        
        file_path = filedialog.asksaveasfilename(
            title=f"Exporter en {format_type.upper()}",
            filetypes=file_types.get(format_type, [("Tous les fichiers", "*.*")]),
            defaultextension=f".{format_type}"
        )
        
        if file_path:
            self.adapter.export_results(file_path, format_type)
    
    def update_statistics(self):
        """Met à jour l'affichage des statistiques"""
        stats = self.adapter.get_statistics()
        
        stats_text = "📊 STATISTIQUES DE SESSION\n"
        stats_text += "=" * 40 + "\n\n"
        
        stats_text += f"📁 Total traité: {stats['total_processed']}\n"
        stats_text += f"✅ Taux de succès: {stats['success_rate']:.1%}\n"
        stats_text += f"💾 Taux de cache: {stats['cache_hit_rate']:.1%}\n"
        stats_text += f"⏱️ Temps moyen: {stats['average_processing_time']:.2f}s\n"
        stats_text += f"🕒 Temps total: {stats['total_processing_time']:.1f}s\n\n"
        
        stats_text += "🎯 SUCCÈS PAR MÉTHODE\n"
        stats_text += "-" * 25 + "\n"
        stats_text += f"🎧 AcoustID: {stats['acousticid_successes']}\n"
        stats_text += f"📊 Spectral: {stats['spectral_successes']}\n" 
        stats_text += f"🎼 MusicBrainz: {stats['musicbrainz_successes']}\n\n"
        
        stats_text += f"🔍 Révisions manuelles: {stats['manual_reviews']}\n"
        stats_text += f"❌ Erreurs: {stats['errors']}\n"
        stats_text += f"🗂️ Fichiers corrompus: {stats['corrupted_files_count']}\n"
        stats_text += f"👆 Sélections manuelles: {stats['manual_selections_count']}\n"
        
        # Nettoyer et afficher
        self.stats_text.delete('1.0', 'end')
        self.stats_text.insert('1.0', stats_text)

    # === GESTION DES PARAMÈTRES ===
    
    def setup_auto_save(self):
        """Configure la sauvegarde automatique des paramètres"""
        # Ajouter des traces pour sauvegarder automatiquement quand les paramètres changent
        self.source_directory.trace_add('write', self.on_setting_changed)
        self.api_key.trace_add('write', self.on_setting_changed)
        
        # Trace pour les seuils
        self.acoustid_threshold.trace_add('write', self.on_setting_changed)
        self.musicbrainz_threshold.trace_add('write', self.on_setting_changed)
        self.spectral_threshold.trace_add('write', self.on_setting_changed)
        
        # Trace pour les options avancées
        self.skip_corrupted.trace_add('write', self.on_setting_changed)
        self.enable_manual_selection.trace_add('write', self.on_setting_changed)
        self.enable_deep_cache.trace_add('write', self.on_setting_changed)
    
    def load_settings(self):
        """Charge les paramètres sauvegardés depuis le fichier JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Charger les paramètres avec des valeurs par défaut
                self.source_directory.set(settings.get('source_directory', ''))
                self.api_key.set(settings.get('api_key', ''))
                
                # Charger les seuils
                self.acoustid_threshold.set(settings.get('acoustid_threshold', 0.85))
                self.musicbrainz_threshold.set(settings.get('musicbrainz_threshold', 0.70))
                self.spectral_threshold.set(settings.get('spectral_threshold', 0.70))
                
                # Charger les options avancées
                self.skip_corrupted.set(settings.get('skip_corrupted', False))  # Désactivé par défaut
                self.enable_manual_selection.set(settings.get('enable_manual_selection', True))
                self.enable_deep_cache.set(settings.get('enable_deep_cache', True))
                
                # Charger les méthodes
                self.enable_acousticid.set(settings.get('enable_acousticid', True))
                self.enable_spectral.set(settings.get('enable_spectral', True))
                self.enable_musicbrainz.set(settings.get('enable_musicbrainz', True))
                self.enable_metadata.set(settings.get('enable_metadata', True))
                
                print(f"💾 Paramètres chargés depuis {self.config_file}")
                
                # Mettre à jour les labels après le chargement
                self.update_threshold_labels()
                
        except Exception as e:
            print(f"⚠️ Impossible de charger les paramètres: {e}")
    
    def update_threshold_labels(self):
        """Met à jour les labels des seuils avec les valeurs actuelles"""
        if hasattr(self, 'acoustid_label'):
            self.acoustid_label.set(f"AcoustID (recommandé: 0.85): {self.acoustid_threshold.get():.2f}")
        if hasattr(self, 'musicbrainz_label'):
            self.musicbrainz_label.set(f"MusicBrainz (recommandé: 0.70): {self.musicbrainz_threshold.get():.2f}")
        if hasattr(self, 'spectral_label'):
            self.spectral_label.set(f"Analyse Spectrale (recommandé: 0.70): {self.spectral_threshold.get():.2f}")
    
    def save_settings(self):
        """Sauvegarde les paramètres actuels dans le fichier JSON"""
        try:
            # Créer le répertoire config s'il n'existe pas
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            settings = {
                'source_directory': self.source_directory.get(),
                'api_key': self.api_key.get(),
                'acoustid_threshold': self.acoustid_threshold.get(),
                'musicbrainz_threshold': self.musicbrainz_threshold.get(),
                'spectral_threshold': self.spectral_threshold.get(),
                'skip_corrupted': self.skip_corrupted.get(),
                'enable_manual_selection': self.enable_manual_selection.get(),
                'enable_deep_cache': self.enable_deep_cache.get(),
                'enable_acousticid': self.enable_acousticid.get(),
                'enable_spectral': self.enable_spectral.get(),
                'enable_musicbrainz': self.enable_musicbrainz.get(),
                'enable_metadata': self.enable_metadata.get()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Paramètres sauvegardés dans {self.config_file}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
    
    def on_setting_changed(self, *args):
        """Appelé automatiquement quand un paramètre change pour sauvegarder"""
        self.save_settings()
    
    def on_closing(self):
        """Gestionnaire de fermeture de l'application"""
        # Arrêter le traitement en cours
        if hasattr(self.adapter, 'is_processing') and self.adapter.is_processing:
            self.adapter.stop_processing()
        
        # Sauvegarder une dernière fois les paramètres
        self.save_settings()
        # Fermer l'application
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        self.root.mainloop()


class ManualSelectionDialog:
    """Dialogue pour la sélection manuelle des résultats MusicBrainz"""
    
    def __init__(self, parent, file_path: str, candidates: List[Dict[str, Any]]):
        self.parent = parent
        self.file_path = file_path
        self.candidates = candidates
        self.selected_candidate = None
        
    def show(self) -> Dict[str, Any]:
        """Affiche le dialogue et retourne le candidat sélectionné"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"🎼 Sélection Manuelle - {Path(self.file_path).name}")
        dialog.geometry("700x500")
        dialog.modal = True
        dialog.grab_set()
        
        # Instructions
        info_label = ttk.Label(dialog, 
            text=f"Plusieurs résultats trouvés pour '{Path(self.file_path).name}'. Sélectionnez le bon:",
            font=('', 10, 'bold'))
        info_label.pack(pady=10)
        
        # Liste des candidats
        candidates_frame = ttk.Frame(dialog)
        candidates_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview pour les candidats
        columns = ('Confiance', 'Artiste', 'Titre', 'Album', 'Année')
        candidates_tree = ttk.Treeview(candidates_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            candidates_tree.heading(col, text=col)
            candidates_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(candidates_frame, orient='vertical', command=candidates_tree.yview)
        candidates_tree.configure(yscrollcommand=scrollbar.set)
        
        # Ajouter les candidats
        for i, candidate in enumerate(self.candidates):
            candidates_tree.insert('', 'end', values=(
                f"{candidate.get('confidence', 0):.2f}",
                candidate.get('artist', ''),
                candidate.get('title', ''),
                candidate.get('album', ''),
                candidate.get('year', '')
            ), tags=(str(i),))
        
        candidates_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Boutons
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(pady=10)
        
        def on_select():
            selection = candidates_tree.selection()
            if selection:
                index = int(candidates_tree.item(selection[0])['tags'][0])
                self.selected_candidate = self.candidates[index]
                dialog.destroy()
        
        def on_skip():
            self.selected_candidate = None
            dialog.destroy()
        
        ttk.Button(buttons_frame, text="✅ Sélectionner", command=on_select).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="⏭️ Ignorer", command=on_skip).pack(side='left', padx=5)
        
        # Double-clic pour sélectionner
        candidates_tree.bind('<Double-1>', lambda e: on_select())
        
        # Centrer le dialogue
        dialog.transient(self.parent)
        dialog.wait_window(dialog)
        
        return self.selected_candidate


def main():
    """Point d'entrée principal"""
    print("🎵 Lancement de MusicFolderManager - Version Complète Enhanced")
    
    # Créer et lancer l'interface
    app = CompleteMusicManagerGUI()
    app.run()


if __name__ == "__main__":
    main()
