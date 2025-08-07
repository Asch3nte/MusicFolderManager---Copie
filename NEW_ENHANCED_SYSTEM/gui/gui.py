"""
Interface utilisateur complète pour Enhanced Music Manager
Inclut toutes les fonctionnalités manquantes et une interface moderne
"""

print("🔍 Debug: Début du module complete_music_gui.py")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import os
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
    ENHANCED_CORE_AVAILABLE = False
    raise ImportError(f"Impossible d'importer les modules Enhanced: {e}")

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
        self.adapter = EnhancedUnifiedAdapter()
        # Configurer les callbacks
        self.adapter.set_callbacks(
            progress_callback=self.on_progress_update,
            status_callback=self.on_status_update,
            result_callback=self.on_results_ready,
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
        
        # Zone de statut avec défilement et logs détaillés
        status_frame = ttk.Frame(progress_group)
        status_frame.pack(fill='x', pady=5)
        
        # Boutons de contrôle des logs
        log_controls = ttk.Frame(status_frame)
        log_controls.pack(fill='x', pady=(0,5))
        
        ttk.Button(log_controls, text="🧹 Effacer Logs", 
                  command=self.clear_logs).pack(side='left', padx=5)
        ttk.Button(log_controls, text="🔍 Logs Détaillés", 
                  command=self.open_detailed_logs_window).pack(side='right', padx=5)
        
        # Checkboxes pour filtrer les logs
        self.show_detailed_logs = tk.BooleanVar(value=True)
        self.show_api_logs = tk.BooleanVar(value=True)
        self.show_spectral_logs = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(log_controls, text="📊 Logs Détaillés", 
                       variable=self.show_detailed_logs).pack(side='left', padx=5)
        ttk.Checkbutton(log_controls, text="🌐 Logs API", 
                       variable=self.show_api_logs).pack(side='left', padx=5)
        ttk.Checkbutton(log_controls, text="📈 Logs Spectral", 
                       variable=self.show_spectral_logs).pack(side='left', padx=5)
        
        # Zone de texte avec couleurs pour les logs
        self.status_text = tk.Text(status_frame, height=8, wrap='word', font=('Consolas', 9))
        status_scroll = ttk.Scrollbar(status_frame, orient='vertical', command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scroll.set)
        
        # Configuration des couleurs pour les différents types de logs
        self.status_text.tag_configure("INFO", foreground="#0066CC")
        self.status_text.tag_configure("SUCCESS", foreground="#008000")
        self.status_text.tag_configure("ERROR", foreground="#FF0000")
        self.status_text.tag_configure("WARNING", foreground="#FF8800")
        self.status_text.tag_configure("SPECTRAL", foreground="#8A2BE2")
        self.status_text.tag_configure("API", foreground="#FF6347")
        self.status_text.tag_configure("FINGERPRINT", foreground="#4682B4")
        self.status_text.tag_configure("CACHE", foreground="#708090")
        
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
    
    def on_status_update(self, message: str, level: str = "INFO"):
        """Callback de statut avec support des niveaux de log et filtrage"""
        import time
        
        # Vérifier les filtres
        if level == "SPECTRAL" and not self.show_spectral_logs.get():
            return
        if level == "API" and not self.show_api_logs.get():
            return
        if level in ["FINGERPRINT", "CACHE"] and not self.show_detailed_logs.get():
            return
        
        # Ajouter timestamp
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Insérer avec la couleur appropriée
        self.status_text.insert('end', formatted_message, level)
        self.status_text.see('end')
        self.root.update_idletasks()
    
    def clear_logs(self):
        """Efface la console de logs"""
        self.status_text.delete('1.0', 'end')
        self.on_status_update("🧹 Console de logs effacée", "INFO")
    
    def open_detailed_logs_window(self):
        """Ouvre une fenêtre détaillée et redimensionnable pour les logs"""
        # Vérifier si la fenêtre existe déjà
        if hasattr(self, 'detailed_logs_window') and self.detailed_logs_window.winfo_exists():
            # Mettre la fenêtre au premier plan
            self.detailed_logs_window.lift()
            self.detailed_logs_window.focus()
            return
        
        # Créer la fenêtre de logs détaillés
        self.detailed_logs_window = tk.Toplevel(self.root)
        self.detailed_logs_window.title("🔍 Logs Détaillés - Enhanced Music Manager")
        self.detailed_logs_window.geometry("900x600")
        self.detailed_logs_window.minsize(600, 400)
        
        # Configuration de la fenêtre
        main_frame = ttk.Frame(self.detailed_logs_window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # === EN-TÊTE ===
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0,10))
        
        title_label = ttk.Label(header_frame, text="📊 Console de Logs Détaillés", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(side='left')
        
        # Boutons de contrôle
        controls_frame = ttk.Frame(header_frame)
        controls_frame.pack(side='right')
        
        ttk.Button(controls_frame, text="🧹 Effacer", 
                  command=self.clear_detailed_logs).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="💾 Sauvegarder", 
                  command=self.save_logs_to_file).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="🔄 Actualiser", 
                  command=self.refresh_detailed_logs).pack(side='left', padx=2)
        
        # === FILTRES ===
        filters_frame = ttk.LabelFrame(main_frame, text="🎯 Filtres de Logs", padding=5)
        filters_frame.pack(fill='x', pady=(0,10))
        
        # Première ligne de filtres
        filters_row1 = ttk.Frame(filters_frame)
        filters_row1.pack(fill='x')
        
        self.detailed_show_info = tk.BooleanVar(value=True)
        self.detailed_show_success = tk.BooleanVar(value=True)
        self.detailed_show_warning = tk.BooleanVar(value=True)
        self.detailed_show_error = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(filters_row1, text="ℹ️ Info", 
                       variable=self.detailed_show_info,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row1, text="✅ Succès", 
                       variable=self.detailed_show_success,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row1, text="⚠️ Warnings", 
                       variable=self.detailed_show_warning,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row1, text="❌ Erreurs", 
                       variable=self.detailed_show_error,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        
        # Deuxième ligne de filtres
        filters_row2 = ttk.Frame(filters_frame)
        filters_row2.pack(fill='x', pady=(5,0))
        
        self.detailed_show_spectral = tk.BooleanVar(value=True)
        self.detailed_show_api = tk.BooleanVar(value=True)
        self.detailed_show_fingerprint = tk.BooleanVar(value=True)
        self.detailed_show_cache = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(filters_row2, text="📈 Spectral", 
                       variable=self.detailed_show_spectral,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row2, text="🌐 API", 
                       variable=self.detailed_show_api,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row2, text="🎧 Fingerprint", 
                       variable=self.detailed_show_fingerprint,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        ttk.Checkbutton(filters_row2, text="💾 Cache", 
                       variable=self.detailed_show_cache,
                       command=self.update_detailed_logs_filter).pack(side='left', padx=5)
        
        # === RECHERCHE ===
        search_frame = ttk.LabelFrame(main_frame, text="🔍 Recherche de Texte", padding=5)
        search_frame.pack(fill='x', pady=(0,10))
        
        search_controls = ttk.Frame(search_frame)
        search_controls.pack(fill='x')
        
        ttk.Label(search_controls, text="Chercher:").pack(side='left', padx=(0,5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_controls, textvariable=self.search_var, width=30)
        self.search_entry.pack(side='left', padx=(0,5))
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        self.search_entry.bind('<Return>', self.search_next)
        
        ttk.Button(search_controls, text="🔍 Suivant", 
                  command=self.search_next).pack(side='left', padx=2)
        ttk.Button(search_controls, text="🔙 Précédent", 
                  command=self.search_previous).pack(side='left', padx=2)
        ttk.Button(search_controls, text="🧹 Effacer", 
                  command=self.clear_search).pack(side='left', padx=2)
        
        # Variables de recherche
        self.search_index = 0
        self.search_matches = []
        
        # === ZONE DE LOGS ===
        logs_frame = ttk.LabelFrame(main_frame, text="📝 Messages de Logs", padding=5)
        logs_frame.pack(fill='both', expand=True)
        
        # Zone de texte avec scrollbars
        text_frame = ttk.Frame(logs_frame)
        text_frame.pack(fill='both', expand=True)
        
        self.detailed_logs_text = tk.Text(text_frame, wrap='word', font=('Consolas', 10))
        
        # Scrollbars
        v_scroll_detailed = ttk.Scrollbar(text_frame, orient='vertical', command=self.detailed_logs_text.yview)
        h_scroll_detailed = ttk.Scrollbar(text_frame, orient='horizontal', command=self.detailed_logs_text.xview)
        self.detailed_logs_text.configure(yscrollcommand=v_scroll_detailed.set, xscrollcommand=h_scroll_detailed.set)
        
        # Configuration des couleurs (identiques à la console principale)
        self.detailed_logs_text.tag_configure("INFO", foreground="#0066CC")
        self.detailed_logs_text.tag_configure("SUCCESS", foreground="#008000")
        self.detailed_logs_text.tag_configure("ERROR", foreground="#FF0000")
        self.detailed_logs_text.tag_configure("WARNING", foreground="#FF8800")
        self.detailed_logs_text.tag_configure("SPECTRAL", foreground="#8A2BE2")
        self.detailed_logs_text.tag_configure("API", foreground="#FF6347")
        self.detailed_logs_text.tag_configure("FINGERPRINT", foreground="#4682B4")
        self.detailed_logs_text.tag_configure("CACHE", foreground="#708090")
        
        # Pack des composants
        self.detailed_logs_text.pack(side='left', fill='both', expand=True)
        v_scroll_detailed.pack(side='right', fill='y')
        h_scroll_detailed.pack(side='bottom', fill='x')
        
        # === BARRE DE STATUT ===
        status_frame_detailed = ttk.Frame(main_frame)
        status_frame_detailed.pack(fill='x', pady=(10,0))
        
        self.detailed_logs_status = tk.StringVar(value="📊 Logs détaillés prêts")
        ttk.Label(status_frame_detailed, textvariable=self.detailed_logs_status).pack(side='left')
        
        # Copier le contenu actuel de la console principale
        self.refresh_detailed_logs()
        
        # Configurer la fermeture
        self.detailed_logs_window.protocol("WM_DELETE_WINDOW", self.on_detailed_logs_close)
    
    def clear_detailed_logs(self):
        """Efface la console de logs détaillés"""
        if hasattr(self, 'detailed_logs_text'):
            self.detailed_logs_text.delete('1.0', 'end')
            self.detailed_logs_status.set("🧹 Logs détaillés effacés")
    
    def save_logs_to_file(self):
        """Sauvegarde les logs dans un fichier"""
        try:
            from tkinter import filedialog
            import datetime
            
            # Créer un nom de fichier par défaut
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"enhanced_music_manager_logs_{timestamp}.txt"
            
            # Demander à l'utilisateur où sauvegarder
            file_path = filedialog.asksaveasfilename(
                title="Sauvegarder les logs",
                defaultextension=".txt",
                filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")],
                initialvalue=default_name
            )
            
            if file_path:
                # Récupérer le contenu des logs
                logs_content = self.status_text.get('1.0', 'end-1c')
                
                # Ajouter un en-tête
                header = f"""
===== LOGS ENHANCED MUSIC MANAGER =====
Date de génération: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Système: Enhanced Music Manager
Version: 2.0
========================================

"""
                
                # Écrire dans le fichier
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(header + logs_content)
                
                self.on_status_update(f"💾 Logs sauvegardés: {file_path}", "SUCCESS")
                if hasattr(self, 'detailed_logs_status'):
                    self.detailed_logs_status.set(f"💾 Sauvegardé: {file_path}")
                    
        except Exception as e:
            self.on_status_update(f"❌ Erreur sauvegarde logs: {str(e)}", "ERROR")
    
    def refresh_detailed_logs(self):
        """Actualise le contenu de la fenêtre de logs détaillés"""
        if hasattr(self, 'detailed_logs_text'):
            # Effacer le contenu actuel
            self.detailed_logs_text.delete('1.0', 'end')
            
            # Copier le contenu de la console principale
            main_logs_content = self.status_text.get('1.0', 'end-1c')
            
            # Analyser et afficher ligne par ligne avec les bons tags
            lines = main_logs_content.split('\n')
            for line in lines:
                if line.strip():
                    # Déterminer le niveau du log basé sur les icônes
                    level = "INFO"
                    if "✅" in line or "🟢" in line:
                        level = "SUCCESS"
                    elif "❌" in line or "💥" in line:
                        level = "ERROR"
                    elif "⚠️" in line or "🟡" in line:
                        level = "WARNING"
                    elif "📈" in line or "📊" in line:
                        level = "SPECTRAL"
                    elif "🌐" in line or "API" in line:
                        level = "API"
                    elif "🎧" in line or "fingerprint" in line or "empreinte" in line:
                        level = "FINGERPRINT"
                    elif "💾" in line or "cache" in line:
                        level = "CACHE"
                    
                    # Ajouter la ligne avec le bon tag
                    self.detailed_logs_text.insert('end', line + '\n', level)
            
            # Aller à la fin
            self.detailed_logs_text.see('end')
            self.update_detailed_logs_filter()
            
            if hasattr(self, 'detailed_logs_status'):
                total_lines = len([l for l in lines if l.strip()])
                self.detailed_logs_status.set(f"🔄 Actualisé - {total_lines} lignes de logs")
    
    def update_detailed_logs_filter(self):
        """Met à jour l'affichage des logs selon les filtres sélectionnés"""
        if not hasattr(self, 'detailed_logs_text'):
            return
        
        # Récupérer tous les tags
        all_tags = ["INFO", "SUCCESS", "ERROR", "WARNING", "SPECTRAL", "API", "FINGERPRINT", "CACHE"]
        
        # Masquer/Afficher selon les filtres
        for tag in all_tags:
            if tag == "INFO" and not self.detailed_show_info.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "SUCCESS" and not self.detailed_show_success.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "ERROR" and not self.detailed_show_error.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "WARNING" and not self.detailed_show_warning.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "SPECTRAL" and not self.detailed_show_spectral.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "API" and not self.detailed_show_api.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "FINGERPRINT" and not self.detailed_show_fingerprint.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            elif tag == "CACHE" and not self.detailed_show_cache.get():
                self.detailed_logs_text.tag_configure(tag, elide=True)
            else:
                self.detailed_logs_text.tag_configure(tag, elide=False)
    
    def on_detailed_logs_close(self):
        """Gestionnaire de fermeture de la fenêtre de logs détaillés"""
        if hasattr(self, 'detailed_logs_window'):
            self.detailed_logs_window.destroy()
            delattr(self, 'detailed_logs_window')
    
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
        detail_window.geometry("700x600")
        
        # Zone de texte avec les détails
        text_widget = tk.Text(detail_window, wrap='word', font=('Consolas', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Formater les détails
        details = f"📁 Fichier: {result.file_path}\n\n"
        details += f"📊 Statut: {result.status.value}\n"
        details += f"🎯 Méthode gagnante: {result.method_used.value if result.method_used else 'Aucune'}\n"
        details += f"📈 Confiance finale: {result.confidence:.2f}\n"
        details += f"⏱️ Temps de traitement: {result.processing_time:.2f}s\n"
        details += f"💾 Cache: {'Oui' if result.cache_hit else 'Non'}\n\n"
        
        # === RÉSULTATS DÉTAILLÉS PAR MÉTHODE ===
        details += "🔬 RÉSULTATS DÉTAILLÉS PAR MÉTHODE\n"
        details += "=" * 50 + "\n\n"
        
        # AcoustID
        details += "🎧 ACOUSTID:\n"
        if result.acoustid_result:
            if result.acoustid_result.get('success'):
                conf = result.acoustid_result.get('confidence', 0)
                meta = result.acoustid_result.get('metadata', {})
                details += f"   ✅ Succès (confiance: {conf:.3f})\n"
                if meta.get('artist'):
                    details += f"   👤 Artiste: {meta.get('artist')}\n"
                if meta.get('title'):
                    details += f"   🎵 Titre: {meta.get('title')}\n"
                if meta.get('album'):
                    details += f"   💿 Album: {meta.get('album')}\n"
                if meta.get('year'):
                    details += f"   📅 Année: {meta.get('year')}\n"
            else:
                error = result.acoustid_result.get('error', 'Échec')
                details += f"   ❌ Échec: {error}\n"
        else:
            details += "   ⚪ Non testé\n"
        details += "\n"
        
        # Spectral
        details += "📊 ANALYSE SPECTRALE:\n"
        if result.spectral_result:
            if result.spectral_result.get('success'):
                conf = result.spectral_result.get('confidence', 0)
                meta = result.spectral_result.get('metadata', {})
                details += f"   ✅ Succès (confiance: {conf:.3f})\n"
                if meta.get('artist'):
                    details += f"   👤 Artiste: {meta.get('artist')}\n"
                if meta.get('title'):
                    details += f"   🎵 Titre: {meta.get('title')}\n"
                if meta.get('genre'):
                    details += f"   🎭 Genre: {meta.get('genre')}\n"
                if meta.get('style'):
                    details += f"   🎨 Style: {meta.get('style')}\n"
            else:
                error = result.spectral_result.get('error', 'Échec')
                details += f"   ❌ Échec: {error}\n"
        else:
            details += "   ⚪ Non testé\n"
        details += "\n"
        
        # MusicBrainz
        details += "🌐 MUSICBRAINZ:\n"
        if result.musicbrainz_result:
            if result.musicbrainz_result.get('success'):
                conf = result.musicbrainz_result.get('confidence', 0)
                meta = result.musicbrainz_result.get('metadata', {})
                details += f"   ✅ Succès (confiance: {conf:.3f})\n"
                if meta.get('artist'):
                    details += f"   👤 Artiste: {meta.get('artist')}\n"
                if meta.get('title'):
                    details += f"   🎵 Titre: {meta.get('title')}\n"
                if meta.get('album'):
                    details += f"   💿 Album: {meta.get('album')}\n"
            else:
                error = result.musicbrainz_result.get('error', 'Échec')
                details += f"   ❌ Échec: {error}\n"
        else:
            details += "   ⚪ Non testé\n"
        details += "\n"
        
        # Last.fm (si disponible)
        if hasattr(result, 'lastfm_result') and result.lastfm_result:
            details += "🎵 LAST.FM:\n"
            if result.lastfm_result.get('success'):
                conf = result.lastfm_result.get('confidence', 0)
                meta = result.lastfm_result.get('metadata', {})
                details += f"   ✅ Succès (confiance: {conf:.3f})\n"
                if meta.get('artist'):
                    details += f"   👤 Artiste: {meta.get('artist')}\n"
                if meta.get('title'):
                    details += f"   🎵 Titre: {meta.get('title')}\n"
            else:
                error = result.lastfm_result.get('error', 'Échec')
                details += f"   ❌ Échec: {error}\n"
            details += "\n"
        
        # === MÉTADONNÉES FINALES ===
        if result.metadata:
            details += "🎵 MÉTADONNÉES FINALES:\n"
            details += "=" * 30 + "\n"
            for key, value in result.metadata.items():
                if value:
                    details += f"   {key}: {value}\n"
            details += "\n"
        
        # === PROPRIÉTÉS AUDIO ===
        if result.audio_properties:
            details += "📀 PROPRIÉTÉS AUDIO:\n"
            details += "=" * 25 + "\n"
            for key, value in result.audio_properties.items():
                details += f"   {key}: {value}\n"
            details += "\n"
        
        # === ERREURS ET SUGGESTIONS ===
        if result.errors:
            details += "❌ ERREURS:\n"
            for error in result.errors:
                details += f"   • {error}\n"
            details += "\n"
        
        if result.suggestions:
            details += "💡 SUGGESTIONS:\n"
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
    """Dialogue pour la sélection manuelle des résultats MusicBrainz avec interface complète"""
    
    def __init__(self, parent, file_path: str, candidates: List[Dict[str, Any]]):
        self.parent = parent
        self.file_path = file_path
        self.candidates = candidates
        self.selected_candidate = None
        self.selected_choices = {}  # Pour stocker les choix multiples
        
    def show(self) -> Dict[str, Any]:
        """Affiche le dialogue et retourne le candidat sélectionné"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"🎼 Sélection Manuelle - {Path(self.file_path).name}")
        self.dialog.geometry("900x700")
        self.dialog.modal = True
        self.dialog.grab_set()
        
        # Créer l'interface complète
        self.setup_manual_selection_ui()
        
        # Centrer le dialogue
        self.dialog.transient(self.parent)
        self.dialog.wait_window(self.dialog)
        
        return self.selected_candidate
    
    def setup_manual_selection_ui(self):
        """Configure l'interface de sélection manuelle complète"""
        
        # === EN-TÊTE ===
        header_frame = ttk.Frame(self.dialog)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        # Informations du fichier
        file_info = ttk.LabelFrame(header_frame, text="📁 Fichier à Analyser", padding=10)
        file_info.pack(fill='x', pady=(0,10))
        
        filename = Path(self.file_path).name
        ttk.Label(file_info, text=f"🎵 Fichier: {filename}", font=('Arial', 11, 'bold')).pack(anchor='w')
        ttk.Label(file_info, text=f"📁 Chemin: {self.file_path}", font=('Arial', 9)).pack(anchor='w')
        
        try:
            file_size = os.path.getsize(self.file_path) / (1024 * 1024)
            ttk.Label(file_info, text=f"📊 Taille: {file_size:.1f} MB", font=('Arial', 9)).pack(anchor='w')
        except:
            pass
        
        # === SECTION PRINCIPALE ===
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        # === SUGGESTIONS MUSICBRAINZ ===
        suggestions_frame = ttk.LabelFrame(main_frame, text="🎼 Suggestions MusicBrainz", padding=10)
        suggestions_frame.pack(fill='both', expand=True, pady=(0,10))
        
        # Instructions
        instructions = ttk.Label(suggestions_frame, 
            text=f"📋 {len(self.candidates)} suggestion(s) trouvée(s). Sélectionnez la meilleure correspondance:",
            font=('Arial', 10))
        instructions.pack(anchor='w', pady=(0,10))
        
        # Frame avec scrollbar pour les suggestions
        suggestions_container = ttk.Frame(suggestions_frame)
        suggestions_container.pack(fill='both', expand=True)
        
        # Canvas et scrollbar
        canvas = tk.Canvas(suggestions_container)
        scrollbar = ttk.Scrollbar(suggestions_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Ajouter chaque suggestion
        self.suggestion_vars = []  # Pour les radio buttons
        for idx, candidate in enumerate(self.candidates):
            self._create_suggestion_widget(scrollable_frame, idx, candidate)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # === OPTIONS SUPPLÉMENTAIRES ===
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ Options Supplémentaires", padding=10)
        options_frame.pack(fill='x', pady=(0,10))
        
        # Variable pour les radio buttons
        self.selection_var = tk.StringVar(value="suggestion_0" if self.candidates else "manual")
        
        # Option de saisie manuelle
        manual_frame = ttk.Frame(options_frame)
        manual_frame.pack(fill='x', pady=5)
        
        ttk.Radiobutton(manual_frame, text="✏️ Saisie manuelle", 
                       variable=self.selection_var, value="manual").pack(side='left')
        ttk.Button(manual_frame, text="🖊️ Ouvrir Éditeur", 
                  command=self.open_manual_editor).pack(side='right')
        
        # Option d'ignorer
        ignore_frame = ttk.Frame(options_frame)
        ignore_frame.pack(fill='x', pady=5)
        
        ttk.Radiobutton(ignore_frame, text="⏭️ Ignorer ce fichier", 
                       variable=self.selection_var, value="ignore").pack(side='left')
        ttk.Label(ignore_frame, text="(Ne pas traiter maintenant)", 
                 font=('Arial', 9), foreground='gray').pack(side='left', padx=(10,0))
        
        # === BOUTONS D'ACTION ===
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="✅ Appliquer Sélection", 
                  command=self.apply_selection).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="🔄 Rafraîchir", 
                  command=self.refresh_suggestions).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="❌ Annuler", 
                  command=self.cancel_selection).pack(side='right', padx=5)
        
        # Sélectionner automatiquement la première suggestion si disponible
        if self.candidates:
            self.selection_var.set("suggestion_0")
        
        # Bind pour la molette de souris sur le canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def _create_suggestion_widget(self, parent, idx, candidate):
        """Crée un widget pour une suggestion MusicBrainz"""
        
        # Frame principal pour cette suggestion
        suggestion_frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        suggestion_frame.pack(fill='x', pady=5, padx=5)
        
        # Frame pour le radio button et les infos
        header_frame = ttk.Frame(suggestion_frame)
        header_frame.pack(fill='x', padx=10, pady=5)
        
        # Radio button pour sélectionner cette suggestion
        radio_btn = ttk.Radiobutton(header_frame, 
                                   text=f"#{idx+1}", 
                                   variable=self.selection_var, 
                                   value=f"suggestion_{idx}")
        radio_btn.pack(side='left')
        
        # Badge de confiance avec couleur
        confidence = candidate.get('confidence', 0)
        confidence_color = "#2E8B57" if confidence > 0.8 else "#FF8C00" if confidence > 0.6 else "#DC143C"
        
        confidence_frame = ttk.Frame(header_frame)
        confidence_frame.pack(side='right')
        
        confidence_label = tk.Label(confidence_frame, 
                                   text=f"Confiance: {confidence:.1%}",
                                   bg=confidence_color, fg="white", 
                                   font=('Arial', 9, 'bold'),
                                   padx=8, pady=2)
        confidence_label.pack()
        
        # Informations détaillées
        info_frame = ttk.Frame(suggestion_frame)
        info_frame.pack(fill='x', padx=20, pady=(0,10))
        
        # Extraire les informations du candidat
        recording = candidate.get('recording', candidate)
        
        # Artiste
        artist = 'Artiste Inconnu'
        if 'artist-credit' in recording:
            artists = []
            for credit in recording['artist-credit']:
                if isinstance(credit, dict) and 'artist' in credit:
                    artists.append(credit['artist'].get('name', ''))
            if artists:
                artist = ', '.join(artists)
        elif 'artist' in recording:
            artist = recording['artist']
        
        # Titre
        title = recording.get('title', 'Titre inconnu')
        
        # Album et année
        album = 'Album inconnu'
        year = ''
        if 'releases' in recording and recording['releases']:
            release = recording['releases'][0]
            album = release.get('title', 'Album inconnu')
            if 'date' in release:
                year = release['date'][:4] if len(release['date']) >= 4 else release['date']
        elif 'release-list' in recording and recording['release-list']:
            release = recording['release-list'][0]
            album = release.get('title', 'Album inconnu')
            if 'date' in release:
                year = release['date'][:4] if len(release['date']) >= 4 else release['date']
        
        # Affichage des informations
        ttk.Label(info_frame, text=f"🎤 Artiste: {artist}", font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(info_frame, text=f"🎵 Titre: {title}", font=('Arial', 10)).pack(anchor='w')
        ttk.Label(info_frame, text=f"💿 Album: {album}", font=('Arial', 9), foreground='#666666').pack(anchor='w')
        
        if year:
            ttk.Label(info_frame, text=f"📅 Année: {year}", font=('Arial', 9), foreground='#666666').pack(anchor='w')
        
        # ID MusicBrainz (pour debug)
        mb_id = recording.get('id', '')
        if mb_id:
            ttk.Label(info_frame, text=f"🆔 ID: {mb_id}", font=('Arial', 8), foreground='#999999').pack(anchor='w')
        
        # Ligne de séparation si ce n'est pas le dernier
        if idx < len(self.candidates) - 1:
            separator = ttk.Separator(suggestion_frame, orient='horizontal')
            separator.pack(fill='x', padx=10, pady=5)
    
    def open_manual_editor(self):
        """Ouvre l'éditeur de métadonnées manuelles"""
        self.manual_window = tk.Toplevel(self.dialog)
        self.manual_window.title(f"✏️ Saisie Manuelle - {Path(self.file_path).name}")
        self.manual_window.geometry("500x400")
        self.manual_window.grab_set()
        
        # Titre
        title_label = tk.Label(self.manual_window, 
                              text="✏️ Saisie Manuelle des Métadonnées",
                              font=('Arial', 14, 'bold'))
        title_label.pack(pady=15)
        
        # Frame principal
        main_frame = ttk.Frame(self.manual_window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Champs de saisie
        self.manual_fields = {}
        fields_info = [
            ('artist', 'Artiste', '🎤'),
            ('title', 'Titre', '🎵'),
            ('album', 'Album', '💿'),
            ('year', 'Année', '📅'),
            ('genre', 'Genre', '🎼'),
            ('track', 'Piste', '🔢')
        ]
        
        for field, label, icon in fields_info:
            field_frame = ttk.Frame(main_frame)
            field_frame.pack(fill='x', pady=8)
            
            label_widget = ttk.Label(field_frame, text=f"{icon} {label}:", font=('Arial', 11))
            label_widget.pack(anchor='w')
            
            entry = ttk.Entry(field_frame, font=('Arial', 11))
            entry.pack(fill='x', pady=(2,0))
            self.manual_fields[field] = entry
        
        # Boutons
        buttons_frame = ttk.Frame(self.manual_window)
        buttons_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Button(buttons_frame, text="💾 Sauvegarder", 
                  command=self.save_manual_data).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="❌ Annuler", 
                  command=self.manual_window.destroy).pack(side='right', padx=5)
        
        # Focus sur le premier champ
        self.manual_fields['artist'].focus()
    
    def save_manual_data(self):
        """Sauvegarde les données saisies manuellement"""
        manual_data = {}
        for field, entry in self.manual_fields.items():
            value = entry.get().strip()
            if value:
                manual_data[field] = value
        
        # Vérifier qu'au moins artiste et titre sont remplis
        if not (manual_data.get('artist') and manual_data.get('title')):
            messagebox.showwarning("⚠️ Données Incomplètes", 
                                 "Veuillez au minimum renseigner l'artiste et le titre.")
            return
        
        # Stocker les données manuelles
        self.manual_data = manual_data
        self.selection_var.set("manual")
        
        # Fermer la fenêtre
        self.manual_window.destroy()
        
        # Afficher un message de confirmation
        messagebox.showinfo("✅ Données Sauvées", 
                           f"Métadonnées manuelles sauvées:\n{manual_data['artist']} - {manual_data['title']}")
    
    def refresh_suggestions(self):
        """Rafraîchit les suggestions (relance une recherche)"""
        # TODO: Implémenter le rafraîchissement des suggestions
        messagebox.showinfo("🔄 Rafraîchissement", "Fonctionnalité à implémenter: Nouvelle recherche MusicBrainz")
    
    def apply_selection(self):
        """Applique la sélection choisie"""
        selection = self.selection_var.get()
        
        if selection.startswith("suggestion_"):
            # Suggestion MusicBrainz sélectionnée
            idx = int(selection.split("_")[1])
            if 0 <= idx < len(self.candidates):
                self.selected_candidate = {
                    'action': 'accept',
                    'source': 'musicbrainz',
                    'data': self.candidates[idx]
                }
        elif selection == "manual":
            # Saisie manuelle
            if hasattr(self, 'manual_data'):
                self.selected_candidate = {
                    'action': 'manual',
                    'source': 'manual',
                    'data': self.manual_data
                }
            else:
                messagebox.showwarning("⚠️ Saisie Manuelle", 
                                     "Veuillez d'abord saisir les métadonnées manuellement.")
                return
        elif selection == "ignore":
            # Ignorer le fichier
            self.selected_candidate = {
                'action': 'ignore',
                'source': 'user',
                'data': {}
            }
        else:
            messagebox.showwarning("⚠️ Sélection", "Veuillez faire un choix.")
            return
        
        # Fermer le dialogue
        self.dialog.destroy()
    
    def on_search_change(self, event=None):
        """Callback quand le texte de recherche change"""
        search_text = self.search_var.get().lower()
        if not search_text:
            self.clear_search_highlighting()
            return
        
        self.search_in_logs(search_text)
    
    def search_in_logs(self, search_text):
        """Recherche dans les logs et surligne les résultats"""
        if not hasattr(self, 'detailed_logs_text'):
            return
        
        # Effacer les surlignes précédents
        self.clear_search_highlighting()
        
        # Obtenir tout le texte
        content = self.detailed_logs_text.get('1.0', 'end-1c')
        
        # Trouver toutes les occurrences
        self.search_matches = []
        start = 0
        
        while True:
            pos = content.lower().find(search_text, start)
            if pos == -1:
                break
            
            # Convertir la position en index tkinter
            line_start = content.count('\n', 0, pos) + 1
            char_start = pos - content.rfind('\n', 0, pos) - 1
            if char_start < 0:
                char_start = pos
            
            line_end = line_start
            char_end = char_start + len(search_text)
            
            self.search_matches.append((f"{line_start}.{char_start}", f"{line_end}.{char_end}"))
            start = pos + 1
        
        # Surligner toutes les occurrences
        for start_idx, end_idx in self.search_matches:
            self.detailed_logs_text.tag_add("search_highlight", start_idx, end_idx)
        
        # Configurer le style de surligné
        self.detailed_logs_text.tag_configure("search_highlight", 
                                             background="#FFFF00", 
                                             foreground="#000000")
        
        # Aller au premier résultat
        if self.search_matches:
            self.search_index = 0
            self.highlight_current_match()
            self.show_search_status()
    
    def search_next(self):
        """Aller au résultat suivant"""
        if not self.search_matches:
            return
        
        self.search_index = (self.search_index + 1) % len(self.search_matches)
        self.highlight_current_match()
        self.show_search_status()
    
    def search_previous(self):
        """Aller au résultat précédent"""
        if not self.search_matches:
            return
        
        self.search_index = (self.search_index - 1) % len(self.search_matches)
        self.highlight_current_match()
        self.show_search_status()
    
    def highlight_current_match(self):
        """Surligne le résultat actuel en cours"""
        if not self.search_matches:
            return
        
        # Effacer le surligné "current"
        self.detailed_logs_text.tag_remove("current_match", '1.0', 'end')
        
        # Surligner le résultat actuel
        start_idx, end_idx = self.search_matches[self.search_index]
        self.detailed_logs_text.tag_add("current_match", start_idx, end_idx)
        self.detailed_logs_text.tag_configure("current_match", 
                                             background="#FF6600", 
                                             foreground="#FFFFFF")
        
        # Faire défiler vers ce résultat
        self.detailed_logs_text.see(start_idx)
    
    def show_search_status(self):
        """Affiche le statut de la recherche"""
        if self.search_matches:
            status = f"🔍 Résultat {self.search_index + 1}/{len(self.search_matches)}"
        else:
            search_text = self.search_var.get()
            if search_text:
                status = f"🔍 Aucun résultat pour '{search_text}'"
            else:
                status = "📊 Logs détaillés prêts"
        
        if hasattr(self, 'detailed_logs_status'):
            self.detailed_logs_status.set(status)
    
    def clear_search(self):
        """Efface la recherche"""
        self.search_var.set("")
        self.clear_search_highlighting()
        if hasattr(self, 'detailed_logs_status'):
            self.detailed_logs_status.set("📊 Logs détaillés prêts")
    
    def clear_search_highlighting(self):
        """Efface tous les surlignés de recherche"""
        if hasattr(self, 'detailed_logs_text'):
            self.detailed_logs_text.tag_remove("search_highlight", '1.0', 'end')
            self.detailed_logs_text.tag_remove("current_match", '1.0', 'end')
        
        self.search_matches = []
        self.search_index = 0
    
    def cancel_selection(self):
        """Annule la sélection"""
        self.selected_candidate = None
        self.dialog.destroy()


def main():
    """Point d'entrée principal"""
    print("🎵 Lancement de MusicFolderManager - Version Complète Enhanced")
    
    # Créer et lancer l'interface
    app = CompleteMusicManagerGUI()
    app.run()


if __name__ == "__main__":
    main()
