#!/usr/bin/env python3
"""
Interface graphique principale pour MusicFolderManager
Utilise tkinter pour une interface simple et accessible
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import queue
import json
import time
import logging
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

# Configuration du chemin vers fpcalc.exe pour l'interface
CURRENT_DIR = Path(__file__).parent.parent
FPCALC_PATH = CURRENT_DIR / "audio_tools" / "fpcalc.exe"

# Définir la variable d'environnement pour pyacoustid
if FPCALC_PATH.exists():
    os.environ['FPCALC'] = str(FPCALC_PATH)
    print(f"🎵 fpcalc configuré pour l'interface: {FPCALC_PATH}")

from organizer.metadata_manager import MetadataManager
from organizer.file_organizer import FileOrganizer
from fingerprint.processor import AudioFingerprinter
from utils.file_utils import is_audio_file
from errors import ErrorManager, get_error_manager, MessageLevel

class MusicFolderManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MusicFolderManager - Interface Graphique")
        self.root.geometry("1600x700")  # Encore plus large pour accommoder 800px + console
        self.root.minsize(1400, 600)    # Taille minimale adaptée
        
        # Fichier de configuration pour sauvegarder les paramètres utilisateur
        self.config_file = Path(__file__).parent.parent / "config" / "ui_settings.json"
        
        # Variables
        self.selected_directory = tk.StringVar()
        self.api_key = tk.StringVar(value="votre_api_key")
        self.output_directory = tk.StringVar(value="./organized_music")
        self.dry_run = tk.BooleanVar(value=True)
        self.organize_files = tk.BooleanVar(value=False)
        self.create_year_folders = tk.BooleanVar(value=True)
        self.move_files = tk.BooleanVar(value=False)
        
        # Charger les paramètres sauvegardés
        self.load_settings()
        
        # Initialiser le logger pour l'interface
        self.logger = logging.getLogger('MusicFolderManagerGUI')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Ajouter des traces pour sauvegarder automatiquement quand les paramètres changent
        self.selected_directory.trace_add('write', self.on_setting_changed)
        self.api_key.trace_add('write', self.on_setting_changed)
        self.output_directory.trace_add('write', self.on_setting_changed)
        
        # Queue pour la communication entre threads
        self.log_queue = queue.Queue()
        
        # Variables pour les composants
        self.metadata_manager = None
        self.file_organizer = None
        self.fingerprinter = None
        
        # Gestionnaire d'erreurs centralisé
        self.error_manager = get_error_manager()
        self.error_manager.register_handler('gui_logger', self._handle_gui_error)
        
        # Créer l'interface
        self.create_widgets()
        
        # Configurer la fermeture de l'application pour sauvegarder les paramètres
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Démarrer le monitoring des logs
        self.check_log_queue()
    
    def _handle_gui_error(self, error_entry):
        """Gestionnaire spécialisé pour les erreurs de l'interface"""
        # Convertir la sévérité en niveau de log approprié
        severity_map = {
            'critical': 'ERROR',
            'error': 'ERROR', 
            'warning': 'WARNING',
            'info': 'INFO'
        }
        
        level = severity_map.get(error_entry['severity'], 'INFO')
        self.log(error_entry['message'], level)
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface"""
        
        # Style
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Section.TLabel', font=('Arial', 10, 'bold'))
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Titre
        title_label = ttk.Label(main_frame, text="🎵 MusicFolderManager", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Frame horizontal pour la disposition principale (gauche + droite)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame gauche pour le contenu principal (taille fixe mais plus large)
        left_frame = ttk.Frame(content_frame, width=800)  # Augmenté de 600 à 800
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)  # Empêche le frame de se redimensionner selon son contenu
        
        # Frame droite pour la console de logs (s'agrandit)
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Notebook pour organiser les onglets (dans le frame gauche)
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.Y, expand=True)
        
        # Onglet 1: Configuration
        self.create_config_tab(notebook)
        
        # Onglet 2: Analyse
        self.create_analysis_tab(notebook)
        
        # Onglet 3: Révision Manuelle
        self.create_manual_review_tab(notebook)
        
        # Onglet 4: Organisation
        self.create_organization_tab(notebook)
        
        # Frame pour les boutons principaux (dans le frame gauche)
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Boutons principaux
        ttk.Button(button_frame, text="🔍 Analyser", command=self.start_analysis).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="📁 Organiser", command=self.start_organization).pack(side=tk.LEFT, padx=5)
        
        # Console de logs (dans le frame droit, sur toute la hauteur)
        log_frame = ttk.LabelFrame(right_frame, text="📝 Console de logs")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame pour le bouton d'effacement des logs
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        ttk.Button(log_button_frame, text="❌ Effacer Logs", command=self.clear_logs).pack(side=tk.RIGHT)
        
        # Zone de texte pour les logs
        self.log_text = scrolledtext.ScrolledText(log_frame, width=70, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Ajouter des couleurs pour les logs
        self.log_text.tag_configure("INFO", foreground="blue")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("WARNING", foreground="orange")
    
    def create_config_tab(self, notebook):
        """Crée l'onglet de configuration"""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ Configuration")
        
        # Sélection du répertoire
        dir_frame = ttk.LabelFrame(config_frame, text="📂 Répertoire à analyser")
        dir_frame.pack(fill=tk.X, padx=10, pady=5)
        
        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(dir_entry_frame, textvariable=self.selected_directory, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_entry_frame, text="Parcourir", command=self.select_directory).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Configuration API
        api_frame = ttk.LabelFrame(config_frame, text="🔑 Configuration API")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="Clé API AcoustID:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        ttk.Entry(api_frame, textvariable=self.api_key, width=50, show="*").pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Configuration de sortie
        output_frame = ttk.LabelFrame(config_frame, text="📤 Configuration de sortie")
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="Répertoire de sortie:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        output_entry_frame = ttk.Frame(output_frame)
        output_entry_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Entry(output_entry_frame, textvariable=self.output_directory, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_entry_frame, text="Parcourir", command=self.select_output_directory).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Options
        options_frame = ttk.LabelFrame(config_frame, text="🔧 Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Mode simulation (Dry Run)", variable=self.dry_run).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Organiser les fichiers", variable=self.organize_files).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Créer des dossiers par année", variable=self.create_year_folders).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Déplacer les fichiers (au lieu de copier)", variable=self.move_files).pack(anchor=tk.W, padx=5, pady=2)
        
        # Filtres de fichiers
        filter_frame = ttk.LabelFrame(config_frame, text="🔍 Filtres de fichiers")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.skip_corrupt = tk.BooleanVar(value=True)
        self.min_file_size = tk.IntVar(value=1024)  # 1KB minimum
        
        ttk.Checkbutton(filter_frame, text="Ignorer les fichiers corrompus", variable=self.skip_corrupt).pack(anchor=tk.W, padx=5, pady=2)
        
        size_frame = ttk.Frame(filter_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(size_frame, text="Taille minimum (bytes):").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=self.min_file_size, width=10).pack(side=tk.LEFT, padx=(5, 0))
    
    def create_analysis_tab(self, notebook):
        """Crée l'onglet d'analyse"""
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="🔍 Analyse")
        
        # Créer un notebook pour séparer les sections d'analyse
        analysis_notebook = ttk.Notebook(analysis_frame)
        analysis_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 1: Informations générales
        self.create_general_info_tab(analysis_notebook)
        
        # Onglet 2: Détection d'authenticité
        self.create_authenticity_detection_tab(analysis_notebook)
    
    def create_general_info_tab(self, notebook):
        """Crée l'onglet d'informations générales"""
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="📊 Informations")
        
        # Informations sur le répertoire
        directory_frame = ttk.LabelFrame(info_frame, text="📊 Informations sur le répertoire")
        directory_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.info_text = tk.Text(directory_frame, height=6, wrap=tk.WORD)
        info_scrollbar = ttk.Scrollbar(directory_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Barre de progression
        progress_frame = ttk.Frame(info_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(progress_frame, text="Progression:").pack(anchor=tk.W)
        self.progress_var = tk.StringVar(value="Prêt")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
    
    def create_authenticity_detection_tab(self, notebook):
        """Crée l'onglet de détection d'authenticité"""
        auth_frame = ttk.Frame(notebook)
        notebook.add(auth_frame, text="🕵️ Détection d'Authenticité")
        
        # Variables pour les options de détection
        self.auth_check_duration = tk.BooleanVar(value=True)
        self.auth_check_filename = tk.BooleanVar(value=False)  # Désactivé par défaut
        self.auth_check_technical = tk.BooleanVar(value=True)
        self.auth_check_metadata = tk.BooleanVar(value=True)
        self.auth_tolerance_seconds = tk.DoubleVar(value=2.0)
        
        # Variables pour les sous-options techniques
        self.auth_tech_bitrate = tk.BooleanVar(value=True)
        self.auth_tech_format = tk.BooleanVar(value=True)
        self.auth_tech_sample_rate = tk.BooleanVar(value=True)
        self.auth_tech_channels = tk.BooleanVar(value=True)
        
        # Variables pour les sous-options métadonnées
        self.auth_meta_musicbrainz = tk.BooleanVar(value=True)
        self.auth_meta_isrc = tk.BooleanVar(value=True)
        self.auth_meta_year = tk.BooleanVar(value=True)
        self.auth_meta_consistency = tk.BooleanVar(value=True)
        
        # Configuration des options
        config_frame = ttk.LabelFrame(auth_frame, text="⚙️ Options de Détection")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Options principales
        main_options_frame = ttk.Frame(config_frame)
        main_options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Analyse de durée
        duration_frame = ttk.Frame(main_options_frame)
        duration_frame.pack(fill=tk.X, pady=2)
        
        duration_check = ttk.Checkbutton(
            duration_frame, 
            text="⏱️ Comparer les durées", 
            variable=self.auth_check_duration
        )
        duration_check.pack(side=tk.LEFT)
        
        ttk.Label(duration_frame, text="Tolérance (secondes):").pack(side=tk.LEFT, padx=(20, 5))
        tolerance_spinbox = ttk.Spinbox(
            duration_frame, 
            from_=0.5, 
            to=10.0, 
            increment=0.5,
            width=8,
            textvariable=self.auth_tolerance_seconds
        )
        tolerance_spinbox.pack(side=tk.LEFT)
        
        # Analyse du nom de fichier (désactivée par défaut)
        filename_check = ttk.Checkbutton(
            main_options_frame, 
            text="📝 Analyser les noms de fichiers (patterns suspects)", 
            variable=self.auth_check_filename,
            state='disabled'  # Désactivé comme demandé
        )
        filename_check.pack(anchor=tk.W, pady=2)
        
        # Note sur le nom de fichier
        filename_note = ttk.Label(
            main_options_frame, 
            text="   ⚠️ Analyse désactivée - peut générer de faux positifs",
            font=('Arial', 9),
            foreground='gray'
        )
        filename_note.pack(anchor=tk.W, padx=(20, 0))
        
        # Analyse technique avec sous-options
        tech_frame = ttk.Frame(main_options_frame)
        tech_frame.pack(fill=tk.X, pady=2)
        
        tech_check = ttk.Checkbutton(
            tech_frame, 
            text="🔧 Analyser les propriétés techniques", 
            variable=self.auth_check_technical,
            command=self.toggle_tech_options
        )
        tech_check.pack(side=tk.LEFT)
        
        # Sous-options techniques
        self.tech_sub_frame = ttk.Frame(main_options_frame)
        self.tech_sub_frame.pack(fill=tk.X, padx=(20, 0))
        
        tech_options = [
            (self.auth_tech_bitrate, "Bitrate suspects (64, 96, 128, 192, 256 kbps)"),
            (self.auth_tech_format, "Formats suspects (.m4a, .webm, .3gp, .amr)"),
            (self.auth_tech_sample_rate, "Sample rate bas (< 44100 Hz)"),
            (self.auth_tech_channels, "Audio mono (possiblement dégradé)")
        ]
        
        for var, text in tech_options:
            ttk.Checkbutton(self.tech_sub_frame, text=f"   • {text}", variable=var).pack(anchor=tk.W)
        
        # Analyse des métadonnées avec sous-options  
        meta_frame = ttk.Frame(main_options_frame)
        meta_frame.pack(fill=tk.X, pady=2)
        
        meta_check = ttk.Checkbutton(
            meta_frame, 
            text="📋 Analyser les métadonnées", 
            variable=self.auth_check_metadata,
            command=self.toggle_meta_options
        )
        meta_check.pack(side=tk.LEFT)
        
        # Sous-options métadonnées
        self.meta_sub_frame = ttk.Frame(main_options_frame)
        self.meta_sub_frame.pack(fill=tk.X, padx=(20, 0))
        
        meta_options = [
            (self.auth_meta_musicbrainz, "ID MusicBrainz manquant"),
            (self.auth_meta_isrc, "Code ISRC manquant"),
            (self.auth_meta_year, "Année manquante ou invalide"),
            (self.auth_meta_consistency, "Incohérences artiste/album_artist")
        ]
        
        for var, text in meta_options:
            ttk.Checkbutton(self.meta_sub_frame, text=f"   • {text}", variable=var).pack(anchor=tk.W)
        
        # Boutons d'action
        action_frame = ttk.Frame(config_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(
            action_frame, 
            text="🕵️ Lancer la détection d'authenticité", 
            command=self.run_authenticity_detection
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            action_frame, 
            text="📊 Voir les résultats", 
            command=self.show_authenticity_results
        ).pack(side=tk.LEFT)
        
        # Zone de résultats
        results_frame = ttk.LabelFrame(auth_frame, text="📋 Résultats de Détection")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.auth_results_text = scrolledtext.ScrolledText(results_frame, height=15, wrap=tk.WORD)
        self.auth_results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message par défaut
        default_msg = """🕵️ DÉTECTION D'AUTHENTICITÉ DES FICHIERS AUDIO

Cette fonction analyse vos fichiers audio pour détecter d'éventuelles versions non-originales :

⏱️ ANALYSE DE DURÉE :
   • Compare la durée réelle du fichier avec la durée de référence
   • Détecte les coupures, intro/outro ajoutés, etc.

🔧 ANALYSE TECHNIQUE :
   • Bitrate : Détecte les bitrates suspects (re-encodages)
   • Format : Identifie les formats souvent utilisés pour les téléchargements
   • Sample Rate : Repère les fichiers avec qualité dégradée
   • Canaux : Détecte la conversion stéréo → mono

📋 ANALYSE MÉTADONNÉES :
   • Vérifie la présence d'identifiants officiels (MusicBrainz, ISRC)
   • Contrôle la cohérence des informations
   • Détecte les métadonnées incomplètes ou suspectes

💡 CONSEILS :
   • Commencez par sélectionner un répertoire dans l'onglet "Général"
   • Ajustez les options selon vos besoins
   • Les résultats incluent un score de suspicion (0-100)
        """
        
        self.auth_results_text.insert(tk.END, default_msg)
        self.auth_results_text.config(state='disabled')
        
        # Initialiser l'état des sous-options
        self.toggle_tech_options()
        self.toggle_meta_options()
    
    def toggle_tech_options(self):
        """Active/désactive les sous-options techniques"""
        state = 'normal' if self.auth_check_technical.get() else 'disabled'
        for child in self.tech_sub_frame.winfo_children():
            child.configure(state=state)
    
    def toggle_meta_options(self):
        """Active/désactive les sous-options métadonnées"""
        state = 'normal' if self.auth_check_metadata.get() else 'disabled'
        for child in self.meta_sub_frame.winfo_children():
            child.configure(state=state)
    
    def create_manual_review_tab(self, notebook):
        """Crée l'onglet de révision manuelle"""
        review_frame = ttk.Frame(notebook)
        notebook.add(review_frame, text="🔍 Révision Manuelle")
        
        # Créer un Notebook pour séparer les sections
        review_notebook = ttk.Notebook(review_frame)
        review_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Onglet 1: Interface de révision interactive
        self.create_interactive_review_tab(review_notebook)
        
        # Onglet 2: Configuration et statistiques
        self.create_config_stats_tab(review_notebook)
    
    def create_interactive_review_tab(self, notebook):
        """Crée l'onglet de révision interactive"""
        interactive_frame = ttk.Frame(notebook)
        notebook.add(interactive_frame, text="🎼 Révision Interactive")
        
        # Instructions courtes
        instructions_frame = ttk.LabelFrame(interactive_frame, text="📋 Comment utiliser")
        instructions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions_text = "Sélectionnez un fichier ci-dessous pour voir les suggestions et choisir la bonne correspondance."
        tk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT).pack(padx=10, pady=5)
        
        # Bouton pour charger les fichiers en révision
        button_frame = ttk.Frame(interactive_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            button_frame, 
            text="🔄 Charger les fichiers en révision manuelle", 
            command=self.load_manual_review_files
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="💾 Appliquer les choix sélectionnés", 
            command=self.apply_manual_choices
        ).pack(side=tk.LEFT)
        
        # Zone principale avec liste et détails
        main_frame = ttk.Frame(interactive_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Liste des fichiers (gauche)
        files_frame = ttk.LabelFrame(main_frame, text="📁 Fichiers en révision")
        files_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Treeview pour la liste des fichiers
        columns = ('Fichier', 'Statut')
        self.manual_files_tree = ttk.Treeview(files_frame, columns=columns, show='tree headings')
        self.manual_files_tree.heading('#0', text='')
        self.manual_files_tree.heading('Fichier', text='Fichier')
        self.manual_files_tree.heading('Statut', text='Statut')
        self.manual_files_tree.column('#0', width=20)
        self.manual_files_tree.column('Fichier', width=300)
        self.manual_files_tree.column('Statut', width=100)
        
        # Scrollbar pour la liste
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.manual_files_tree.yview)
        self.manual_files_tree.configure(yscrollcommand=files_scrollbar.set)
        
        self.manual_files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Événement de sélection
        self.manual_files_tree.bind('<<TreeviewSelect>>', self.on_manual_file_select)
        
        # Zone de détails et suggestions (droite)
        details_frame = ttk.LabelFrame(main_frame, text="🎼 Suggestions pour le fichier sélectionné")
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Zone d'affichage des suggestions
        self.suggestions_frame = ttk.Frame(details_frame)
        self.suggestions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message par défaut
        self.no_selection_label = tk.Label(
            self.suggestions_frame, 
            text="👆 Sélectionnez un fichier dans la liste pour voir les suggestions",
            font=('Arial', 10),
            fg='gray'
        )
        self.no_selection_label.pack(expand=True)
        
        # Stockage des données de révision
        self.manual_review_data = []
        self.selected_choices = {}  # {file_path: choice_data}
    
    def create_config_stats_tab(self, notebook):
        """Crée l'onglet de configuration et statistiques"""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ Configuration & Stats")
        
        # Instructions détaillées
        instructions_frame = ttk.LabelFrame(config_frame, text="📋 Instructions détaillées")
        instructions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions_text = """
Les fichiers nécessitant une révision manuelle sont ceux pour lesquels :
• Aucune correspondance n'a été trouvée dans AcoustID
• La confiance de l'identification est trop faible
• Les métadonnées suggérées semblent incorrectes

Le bloc statistique vous aide à :
• Comprendre pourquoi certains fichiers échouent
• Ajuster les seuils de confiance pour plus d'automatisation
• Voir les tendances de détection dans votre collection
        """
        
        instructions_label = tk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT, wraplength=800)
        instructions_label.pack(padx=10, pady=5)
        
        # Configuration des seuils
        thresholds_frame = ttk.LabelFrame(config_frame, text="⚙️ Ajustement des Seuils")
        thresholds_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Seuil de confiance AcoustID
        confidence_frame = ttk.Frame(thresholds_frame)
        confidence_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(confidence_frame, text="Seuil de confiance AcoustID (0.0 - 1.0):").pack(side=tk.LEFT)
        self.confidence_threshold = tk.DoubleVar(value=0.85)
        confidence_scale = ttk.Scale(
            confidence_frame, 
            from_=0.0, 
            to=1.0, 
            variable=self.confidence_threshold,
            orient=tk.HORIZONTAL,
            length=200
        )
        confidence_scale.pack(side=tk.LEFT, padx=(10, 5))
        
        self.confidence_label = ttk.Label(confidence_frame, text="0.85")
        self.confidence_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Mettre à jour l'affichage du seuil
        def update_confidence_label(event=None):
            self.confidence_label.config(text=f"{self.confidence_threshold.get():.2f}")
        
        confidence_scale.configure(command=lambda x: update_confidence_label())
        
        # Bouton pour appliquer les nouveaux seuils
        ttk.Button(
            thresholds_frame, 
            text="💾 Appliquer les nouveaux seuils", 
            command=self.apply_new_thresholds
        ).pack(pady=5)
        
        # Statistiques des révisions manuelles
        stats_frame = ttk.LabelFrame(config_frame, text="📊 Statistiques et Diagnostic")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.manual_review_stats = scrolledtext.ScrolledText(stats_frame, height=8, wrap=tk.WORD)
        self.manual_review_stats.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bouton pour afficher les détails
        ttk.Button(
            stats_frame, 
            text="🔄 Actualiser les statistiques", 
            command=self.update_manual_review_stats
        ).pack(pady=5)
    
    def apply_new_thresholds(self):
        """Applique les nouveaux seuils de confiance"""
        try:
            from config.config_manager import ConfigManager
            config = ConfigManager.get_instance()
            
            # Mettre à jour le seuil dans la configuration
            new_threshold = self.confidence_threshold.get()
            config.set('FINGERPRINT', 'acoustid_min_confidence', str(new_threshold))
            config.save()
            
            self.log(f"✅ Nouveau seuil de confiance appliqué: {new_threshold:.2f}", "SUCCESS")
            self.log("💡 Relancez l'analyse pour appliquer le nouveau seuil", "INFO")
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'application du seuil: {e}", "ERROR")
    
    def update_manual_review_stats(self):
        """Met à jour les statistiques de révision manuelle"""
        stats_text = "📊 Statistiques de Révision Manuelle\n"
        stats_text += "=" * 50 + "\n\n"
        
        # Obtenir les statistiques du gestionnaire d'erreurs
        error_stats = self.error_manager.get_statistics()
        
        stats_text += f"Total d'erreurs gérées: {error_stats['total_errors']}\n"
        stats_text += f"Erreurs par catégorie:\n"
        for category, count in error_stats['errors_by_category'].items():
            stats_text += f"  • {category}: {count}\n"
        
        stats_text += f"\nErreurs par sévérité:\n"
        for severity, count in error_stats['errors_by_severity'].items():
            stats_text += f"  • {severity}: {count}\n"
        
        # Statistiques de backup (nouveau système basé sur base de données)
        try:
            from backup import get_backup_statistics
            backup_stats = get_backup_statistics()
            
            stats_text += f"\n📁 Statistiques de Backup (Base de données):\n"
            stats_text += f"Total d'opérations enregistrées: {backup_stats.get('total', 0)}\n"
            
            if backup_stats.get('total', 0) > 0:
                stats_text += "Types d'opérations:\n"
                for operation, info in backup_stats.items():
                    if operation != 'total' and isinstance(info, dict):
                        stats_text += f"  • {operation}: {info['count']} (dernière: {info['last_operation']})\n"
            else:
                stats_text += "Aucune opération de backup enregistrée.\n"
        except Exception as e:
            stats_text += f"\n⚠️ Impossible de récupérer les stats de backup: {e}\n"
        
        # Conseils basés sur les statistiques
        stats_text += "\n" + "=" * 50 + "\n"
        stats_text += "💡 Conseils d'Optimisation:\n\n"
        
        if error_stats['errors_by_severity'].get('warning', 0) > error_stats['errors_by_severity'].get('error', 0):
            stats_text += "• Beaucoup de fichiers nécessitent une révision manuelle\n"
            stats_text += "• Considérez diminuer le seuil de confiance AcoustID\n"
            stats_text += "• Vérifiez la qualité des fichiers audio\n"
        
        if error_stats['total_errors'] == 0:
            stats_text += "• Aucune erreur détectée - configuration optimale !\n"
        
        self.manual_review_stats.delete(1.0, tk.END)
        self.manual_review_stats.insert(tk.END, stats_text)
    
    def load_manual_review_files(self):
        """Charge les fichiers en révision manuelle depuis la dernière analyse"""
        try:
            # Vider la liste et les données
            self.manual_files_tree.delete(*self.manual_files_tree.get_children())
            self.manual_review_data = []
            
            # Si on a des résultats de la dernière analyse, les utiliser
            if hasattr(self, 'last_analysis_results'):
                manual_files = [r for r in self.last_analysis_results if r.get('status') == 'manual_review']
                
                for result in manual_files:
                    file_path = result['file']
                    filename = os.path.basename(file_path)
                    status = "En attente"
                    
                    # Ajouter à la liste
                    item = self.manual_files_tree.insert('', 'end', text='🎵', values=(filename, status))
                    
                    # Stocker les données complètes avec l'ID de l'item
                    self.manual_review_data.append({
                        'item_id': item,
                        'data': result
                    })
                
                self.log(f"✅ {len(manual_files)} fichiers chargés pour révision manuelle", "SUCCESS")
            else:
                self.log("ℹ️ Aucune analyse récente trouvée. Lancez d'abord une analyse.", "INFO")
                
        except Exception as e:
            self.log(f"❌ Erreur lors du chargement: {e}", "ERROR")
    
    def on_manual_file_select(self, event):
        """Appelé quand un fichier est sélectionné dans la liste"""
        selection = self.manual_files_tree.selection()
        if not selection:
            return
        
        try:
            # Effacer la zone des suggestions
            for widget in self.suggestions_frame.winfo_children():
                widget.destroy()
            
            # Récupérer les données du fichier sélectionné
            item = selection[0]
            result = None
            
            # Trouver les données correspondantes
            for data_entry in self.manual_review_data:
                if data_entry['item_id'] == item:
                    result = data_entry['data']
                    break
            
            if not result:
                return
            
            # Afficher les informations du fichier
            file_path = result['file']
            filename = os.path.basename(file_path)
            
            # Titre
            title_label = tk.Label(
                self.suggestions_frame, 
                text=f"🎵 {filename}",
                font=('Arial', 12, 'bold')
            )
            title_label.pack(pady=(0, 10))
            
            # Informations du fichier
            info_frame = tk.Frame(self.suggestions_frame)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            tk.Label(info_frame, text=f"📁 Chemin: {file_path}", anchor='w').pack(fill=tk.X)
            tk.Label(info_frame, text=f"⚠️ Raison: {result.get('reason', 'Inconnue')}", anchor='w').pack(fill=tk.X)
            
            # Section des suggestions
            suggestions_label = tk.Label(
                self.suggestions_frame, 
                text="🎼 Suggestions disponibles:",
                font=('Arial', 10, 'bold')
            )
            suggestions_label.pack(anchor='w', pady=(10, 5))
            
            # Vérifier s'il y a des suggestions MusicBrainz
            if result.get('musicbrainz_suggestions'):
                self._add_musicbrainz_suggestion(result['musicbrainz_suggestions'], file_path)
            
            # Vérifier s'il y a des suggestions AcoustID
            if result.get('acoustid_data'):
                self._add_acoustid_suggestion(result['acoustid_data'], file_path)
            
            # Option de saisie manuelle
            self._add_manual_input_option(file_path)
            
            # Option d'ignorer le fichier
            self._add_ignore_option(file_path)
            
        except Exception as e:
            self.log(f"❌ Erreur lors de l'affichage des suggestions: {e}", "ERROR")
    
    def _add_musicbrainz_suggestion(self, mb_data, file_path):
        """Ajoute les suggestions MusicBrainz (toutes les suggestions disponibles)"""
        if not mb_data:
            return
        
        # Vérifier le nouveau format avec toutes les suggestions
        if 'suggestions' in mb_data:
            suggestions = mb_data['suggestions']
            total_count = mb_data.get('total_count', len(suggestions))
            
            # Titre pour toutes les suggestions
            header_frame = tk.Frame(self.suggestions_frame)
            header_frame.pack(fill=tk.X, pady=(5,0))
            tk.Label(header_frame, text=f"🎼 MusicBrainz - {total_count} suggestion(s) trouvée(s)", 
                    font=('Arial', 10, 'bold')).pack(anchor='w')
            
            # Afficher chaque suggestion
            for idx, suggestion in enumerate(suggestions):
                recording = suggestion['recording']
                confidence = suggestion.get('confidence', 0)
                
                # Extraire les informations
                artist = 'Artiste Inconnu'
                if 'artist-credit' in recording:
                    artists = []
                    for credit in recording['artist-credit']:
                        if isinstance(credit, dict) and 'artist' in credit:
                            artists.append(credit['artist'].get('name', ''))
                    if artists:
                        artist = ', '.join(artists)
                
                title = recording.get('title', 'Titre inconnu')
                
                # Album (si disponible)
                album = 'Album inconnu'
                if 'release-list' in recording and recording['release-list']:
                    album = recording['release-list'][0].get('title', 'Album inconnu')
                
                # Frame pour cette suggestion
                suggestion_frame = tk.Frame(self.suggestions_frame, relief=tk.RIDGE, bd=1)
                suggestion_frame.pack(fill=tk.X, pady=2)
                
                # Informations de la suggestion
                info_frame = tk.Frame(suggestion_frame)
                info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
                
                # Numérotation des suggestions avec couleurs
                rank_label = f"#{idx+1}"
                color = "#2E8B57" if idx == 0 else "#4682B4" if idx < 3 else "#708090"
                
                tk.Label(info_frame, text=f"{rank_label} - Confiance: {confidence:.1%}", 
                        font=('Arial', 9, 'bold'), fg=color).pack(anchor='w')
                tk.Label(info_frame, text=f"Artiste: {artist}").pack(anchor='w')
                tk.Label(info_frame, text=f"Titre: {title}").pack(anchor='w')
                tk.Label(info_frame, text=f"Album: {album}", fg="#666666").pack(anchor='w')
                
                # Bouton pour accepter cette suggestion spécifique
                accept_btn = tk.Button(
                    suggestion_frame, 
                    text="✅ Choisir",
                    bg=color,
                    fg="white",
                    command=lambda s=suggestion: self._accept_suggestion(file_path, 'musicbrainz', s)
                )
                accept_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        else:
            # Format ancien (rétrocompatibilité)
            recording = mb_data.get('recording', {})
            artist = recording.get('artist-credit-phrase', 'Artiste inconnu')
            title = recording.get('title', 'Titre inconnu')
            confidence = mb_data.get('confidence', 0)
            
            # Frame pour cette suggestion
            suggestion_frame = tk.Frame(self.suggestions_frame, relief=tk.RIDGE, bd=1)
            suggestion_frame.pack(fill=tk.X, pady=2)
            
            # Informations de la suggestion
            info_frame = tk.Frame(suggestion_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
            
            tk.Label(info_frame, text=f"🎼 MusicBrainz ({confidence:.1%})", font=('Arial', 9, 'bold')).pack(anchor='w')
            tk.Label(info_frame, text=f"Artiste: {artist}").pack(anchor='w')
            tk.Label(info_frame, text=f"Titre: {title}").pack(anchor='w')
            
            # Bouton pour accepter
            accept_btn = tk.Button(
                suggestion_frame, 
                text="✅ Accepter",
                command=lambda: self._accept_suggestion(file_path, 'musicbrainz', mb_data)
            )
            accept_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _add_acoustid_suggestion(self, acoustid_data, file_path):
        """Ajoute une suggestion AcoustID (si disponible)"""
        if not acoustid_data:
            return
        
        # Simuler des données AcoustID (en réalité, elles seraient dans acoustid_data)
        suggestion_frame = tk.Frame(self.suggestions_frame, relief=tk.RIDGE, bd=1)
        suggestion_frame.pack(fill=tk.X, pady=2)
        
        info_frame = tk.Frame(suggestion_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        tk.Label(info_frame, text="🎵 AcoustID (confiance faible)", font=('Arial', 9, 'bold')).pack(anchor='w')
        tk.Label(info_frame, text="Suggestion AcoustID disponible mais confiance insuffisante").pack(anchor='w')
        
        accept_btn = tk.Button(
            suggestion_frame, 
            text="✅ Accepter quand même",
            command=lambda: self._accept_suggestion(file_path, 'acoustid', acoustid_data)
        )
        accept_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _add_manual_input_option(self, file_path):
        """Ajoute l'option de saisie manuelle"""
        manual_frame = tk.Frame(self.suggestions_frame, relief=tk.RIDGE, bd=1)
        manual_frame.pack(fill=tk.X, pady=2)
        
        info_frame = tk.Frame(manual_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        tk.Label(info_frame, text="✏️ Saisie manuelle", font=('Arial', 9, 'bold')).pack(anchor='w')
        tk.Label(info_frame, text="Entrer les métadonnées manuellement").pack(anchor='w')
        
        manual_btn = tk.Button(
            manual_frame, 
            text="✏️ Saisir",
            command=lambda: self._open_manual_input(file_path)
        )
        manual_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _add_ignore_option(self, file_path):
        """Ajoute l'option d'ignorer le fichier"""
        ignore_frame = tk.Frame(self.suggestions_frame, relief=tk.RIDGE, bd=1)
        ignore_frame.pack(fill=tk.X, pady=2)
        
        info_frame = tk.Frame(ignore_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        tk.Label(info_frame, text="⏭️ Ignorer", font=('Arial', 9, 'bold')).pack(anchor='w')
        tk.Label(info_frame, text="Ne pas traiter ce fichier pour le moment").pack(anchor='w')
        
        ignore_btn = tk.Button(
            ignore_frame, 
            text="⏭️ Ignorer",
            command=lambda: self._ignore_file(file_path)
        )
        ignore_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def _accept_suggestion(self, file_path, source, data):
        """Accepte une suggestion pour un fichier"""
        self.selected_choices[file_path] = {
            'action': 'accept',
            'source': source,
            'data': data
        }
        
        # Mettre à jour le statut dans la liste
        for data_entry in self.manual_review_data:
            result = data_entry['data']
            if result and result['file'] == file_path:
                item = data_entry['item_id']
                self.manual_files_tree.set(item, 'Statut', f'✅ {source}')
                break
        
        self.log(f"✅ Suggestion {source} acceptée pour {os.path.basename(file_path)}", "SUCCESS")
    
    def _ignore_file(self, file_path):
        """Marque un fichier comme ignoré"""
        self.selected_choices[file_path] = {
            'action': 'ignore'
        }
        
        # Mettre à jour le statut dans la liste
        for data_entry in self.manual_review_data:
            result = data_entry['data']
            if result and result['file'] == file_path:
                item = data_entry['item_id']
                self.manual_files_tree.set(item, 'Statut', '⏭️ Ignoré')
                break
        
        self.log(f"⏭️ Fichier ignoré: {os.path.basename(file_path)}", "INFO")
    
    def _open_manual_input(self, file_path):
        """Ouvre une fenêtre de saisie manuelle"""
        # Créer une fenêtre popup pour la saisie manuelle
        manual_window = tk.Toplevel(self.root)
        manual_window.title(f"Saisie manuelle - {os.path.basename(file_path)}")
        manual_window.geometry("400x300")
        
        # Champs de saisie
        tk.Label(manual_window, text="✏️ Saisie manuelle des métadonnées", font=('Arial', 12, 'bold')).pack(pady=10)
        
        fields = {}
        for field, label in [('artist', 'Artiste'), ('title', 'Titre'), ('album', 'Album'), ('year', 'Année')]:
            frame = tk.Frame(manual_window)
            frame.pack(fill=tk.X, padx=20, pady=5)
            
            tk.Label(frame, text=f"{label}:", width=10, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            fields[field] = entry
        
        # Boutons
        button_frame = tk.Frame(manual_window)
        button_frame.pack(pady=20)
        
        def save_manual():
            manual_data = {field: entry.get() for field, entry in fields.items()}
            self.selected_choices[file_path] = {
                'action': 'manual',
                'data': manual_data
            }
            
            # Mettre à jour le statut
            for data_entry in self.manual_review_data:
                result = data_entry['data']
                if result and result['file'] == file_path:
                    item = data_entry['item_id']
                    self.manual_files_tree.set(item, 'Statut', '✏️ Manuel')
                    break
            
            self.log(f"✏️ Métadonnées manuelles saisies pour {os.path.basename(file_path)}", "SUCCESS")
            manual_window.destroy()
        
        tk.Button(button_frame, text="💾 Enregistrer", command=save_manual).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="❌ Annuler", command=manual_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply_manual_choices(self):
        """Applique tous les choix sélectionnés en modifiant réellement les fichiers"""
        if not self.selected_choices:
            self.log("ℹ️ Aucun choix à appliquer", "INFO")
            return
        
        # Importer le gestionnaire de métadonnées
        try:
            from utils.metadata_writer import MetadataWriter
            metadata_writer = MetadataWriter(self.logger)
        except ImportError as e:
            self.log(f"❌ Impossible d'importer le gestionnaire de métadonnées: {e}", "ERROR")
            return
        
        applied_count = 0
        error_count = 0
        
        for file_path, choice in self.selected_choices.items():
            try:
                filename = os.path.basename(file_path)
                
                if choice['action'] == 'accept':
                    # Appliquer la suggestion acceptée
                    source = choice['source']
                    data = choice['data']
                    
                    self.log(f"🔄 Application de la suggestion {source} pour {filename}...", "INFO")
                    
                    if source == 'musicbrainz':
                        # Convertir les données MusicBrainz en métadonnées
                        metadata = metadata_writer.format_musicbrainz_metadata(data)
                        if metadata:
                            success = metadata_writer.apply_metadata(file_path, metadata)
                            if success:
                                self.log(f"✅ Métadonnées MusicBrainz appliquées: {filename}", "SUCCESS")
                                self.log(f"   └─ {metadata.get('artist', 'N/A')} - {metadata.get('title', 'N/A')}", "INFO")
                                applied_count += 1
                            else:
                                self.log(f"❌ Échec de l'application pour {filename}", "ERROR")
                                error_count += 1
                        else:
                            self.log(f"❌ Impossible de formater les métadonnées MusicBrainz pour {filename}", "ERROR")
                            error_count += 1
                    
                    elif source == 'acoustid':
                        # Traiter les données AcoustID (à implémenter si nécessaire)
                        self.log(f"⚠️ Application AcoustID pas encore implémentée pour {filename}", "WARNING")
                        
                elif choice['action'] == 'manual':
                    # Appliquer les métadonnées manuelles
                    manual_data = choice['data']
                    
                    self.log(f"🔄 Application des métadonnées manuelles pour {filename}...", "INFO")
                    
                    # manual_data devrait contenir les champs artist, title, album, etc.
                    success = metadata_writer.apply_metadata(file_path, manual_data)
                    if success:
                        self.log(f"✅ Métadonnées manuelles appliquées: {filename}", "SUCCESS")
                        applied_count += 1
                    else:
                        self.log(f"❌ Échec de l'application manuelle pour {filename}", "ERROR")
                        error_count += 1
                        
                elif choice['action'] == 'ignore':
                    # Fichier ignoré - rien à faire
                    self.log(f"⏭️ Fichier ignoré: {filename}", "INFO")
                    applied_count += 1
                    
            except Exception as e:
                self.log(f"❌ Erreur lors de l'application pour {os.path.basename(file_path)}: {e}", "ERROR")
                error_count += 1
        
        # Résumé
        total = len(self.selected_choices)
        if error_count == 0:
            self.log(f"🎯 Tous les choix appliqués avec succès ! ({applied_count}/{total})", "SUCCESS")
        else:
            self.log(f"⚠️ {applied_count} succès, {error_count} erreurs sur {total} choix", "WARNING")
        
        # Supprimer les fichiers traités avec succès de la liste de révision
        processed_files = set()
        for file_path, choice in self.selected_choices.items():
            try:
                if choice['action'] in ['accept', 'manual', 'ignore']:
                    processed_files.add(file_path)
            except Exception:
                pass
        
        # Retirer ces fichiers de manual_review_data et de la TreeView
        items_to_remove = []
        for data_entry in self.manual_review_data:
            result = data_entry.get('data', {})
            if result and result.get('file') in processed_files:
                # Marquer pour suppression
                items_to_remove.append(data_entry)
                # Supprimer de la TreeView
                try:
                    self.manual_files_tree.delete(data_entry['item_id'])
                except:
                    pass
        
        # Supprimer de manual_review_data
        for item in items_to_remove:
            if item in self.manual_review_data:
                self.manual_review_data.remove(item)
        
        # Vider les choix après application
        self.selected_choices.clear()
        
        # Effacer la zone de suggestions
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        
        # Remettre le message par défaut
        self.no_selection_label = tk.Label(
            self.suggestions_frame, 
            text="👆 Sélectionnez un fichier dans la liste pour voir les suggestions",
            font=('Arial', 10),
            fg='gray'
        )
        self.no_selection_label.pack(expand=True)
        
        self.log(f"✅ {len(processed_files)} fichiers retirés de la liste de révision", "SUCCESS")
    
    def run_authenticity_detection(self):
        """Lance la détection d'authenticité sur le répertoire sélectionné"""
        directory = self.selected_directory.get()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("Erreur", "Veuillez d'abord sélectionner un répertoire dans l'onglet Général")
            return
        
        # Vérifier qu'au moins une analyse est activée
        if not any([
            self.auth_check_duration.get(),
            self.auth_check_filename.get(), 
            self.auth_check_technical.get(),
            self.auth_check_metadata.get()
        ]):
            messagebox.showwarning("Attention", "Veuillez activer au moins une méthode de détection")
            return
        
        # Lancer la détection dans un thread séparé
        self.auth_results_text.config(state='normal')
        self.auth_results_text.delete(1.0, tk.END)
        self.auth_results_text.insert(tk.END, "🔍 Début de la détection d'authenticité...\n\n")
        self.auth_results_text.config(state='disabled')
        
        # Créer et démarrer le thread
        detection_thread = threading.Thread(
            target=self._run_authenticity_detection_thread,
            args=(directory,),
            daemon=True
        )
        detection_thread.start()
    
    def _run_authenticity_detection_thread(self, directory):
        """Thread pour la détection d'authenticité"""
        try:
            # Debug: Vérifier les imports disponibles
            self._update_auth_results("🔍 Vérification des modules...\n")
            
            try:
                from non_original_detector import NonOriginalDetector
                self._update_auth_results("   ✅ NonOriginalDetector disponible\n")
            except ImportError as e:
                self._update_auth_results(f"   ❌ NonOriginalDetector: {e}\n")
                return
            
            try:
                from enhanced_music_processor import EnhancedMusicProcessor
                self._update_auth_results("   ✅ EnhancedMusicProcessor disponible\n")
                processor_available = True
            except ImportError as e:
                self._update_auth_results(f"   ⚠️ EnhancedMusicProcessor: {e}\n")
                self._update_auth_results("   🔄 Mode simplifié activé\n")
                processor_available = False
            
            try:
                from spectral_analyzer import SpectralMatcher
                self._update_auth_results("   ✅ SpectralMatcher disponible\n")
                analyzer_available = True
            except ImportError as e:
                self._update_auth_results(f"   ❌ SpectralMatcher: {e}\n")
                analyzer_available = False
            
            self._update_auth_results("\n")
            
            # Configurer le détecteur selon les options
            tolerance = self.auth_tolerance_seconds.get()
            detector = NonOriginalDetector(tolerance_seconds=tolerance)
            
            # Configurer les options selon les cases cochées
            detector_options = {
                'check_duration': self.auth_check_duration.get(),
                'check_filename': self.auth_check_filename.get(),
                'check_technical': self.auth_check_technical.get(),
                'check_metadata': self.auth_check_metadata.get(),
                'tech_options': {
                    'bitrate': self.auth_tech_bitrate.get(),
                    'format': self.auth_tech_format.get(),
                    'sample_rate': self.auth_tech_sample_rate.get(),
                    'channels': self.auth_tech_channels.get()
                },
                'meta_options': {
                    'musicbrainz': self.auth_meta_musicbrainz.get(),
                    'isrc': self.auth_meta_isrc.get(),
                    'year': self.auth_meta_year.get(),
                    'consistency': self.auth_meta_consistency.get()
                }
            }
            
            # Trouver tous les fichiers audio
            audio_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        audio_files.append(file_path)
            
            total_files = len(audio_files)
            if total_files == 0:
                self._update_auth_results("❌ Aucun fichier audio trouvé dans le répertoire sélectionné\n")
                return
            
            self._update_auth_results(f"📁 Répertoire: {directory}\n")
            self._update_auth_results(f"🎵 {total_files} fichiers audio trouvés\n")
            self._update_auth_results(f"⚙️ Tolérance de durée: {tolerance}s\n")
            self._update_auth_results(f"🔧 Processeur amélioré: {'✅ Disponible' if processor_available else '❌ Mode simplifié'}\n\n")
            
            # Créer le processeur amélioré seulement s'il est disponible
            if processor_available:
                processor = EnhancedMusicProcessor()
            else:
                processor = None
            
            suspicious_files = []
            processed_count = 0
            
            for file_path in audio_files:
                try:
                    filename = os.path.basename(file_path)
                    self._update_auth_results(f"🔍 Analyse: {filename}\n")
                    
                    # Choisir la méthode de traitement selon la disponibilité
                    if processor_available and processor:
                        # Méthode complète avec EnhancedMusicProcessor
                        try:
                            result = processor.process_audio_file(file_path)
                            
                            if not result.get('success'):
                                raise Exception(f"Échec du traitement: {result.get('error', 'Erreur inconnue')}")
                            
                            # Extraire les informations nécessaires
                            actual_duration = result.get('duration', 0)
                            metadata = result.get('metadata', {})
                            reference_duration = metadata.get('duration', 0)
                            
                            # Adapter les métadonnées pour le détecteur
                            detector_metadata = {
                                'title': metadata.get('title', ''),
                                'artist': metadata.get('artist', ''),
                                'album': metadata.get('album', ''),
                                'year': metadata.get('year'),
                                'bitrate': result.get('audio_features', {}).get('bitrate', 0),
                                'format': result.get('format', ''),
                                'sample_rate': result.get('audio_features', {}).get('sample_rate', 0),
                                'channels': result.get('audio_features', {}).get('channels', 2),
                                'musicbrainz_id': metadata.get('musicbrainz_track_id'),
                                'isrc': metadata.get('isrc'),
                                'album_artist': metadata.get('album_artist')
                            }
                            
                            processing_mode = "Complet"
                            
                        except Exception as e:
                            # Si le processeur amélioré échoue, passer au mode simplifié
                            raise Exception(f"EnhancedMusicProcessor failed: {e}")
                            
                    else:
                        # Mode simplifié direct
                        raise Exception("Mode simplifié activé - pas d'EnhancedMusicProcessor")
                    
                    # Lancer l'analyse d'authenticité
                    analysis = detector.full_analysis(
                        file_path=file_path,
                        actual_duration=actual_duration,
                        reference_duration=reference_duration,
                        metadata=detector_metadata
                    )
                    
                    # Afficher les résultats
                    score = analysis['suspicion_score']
                    verdict = analysis['verdict_text']
                    
                    if score >= 15:  # Fichier suspect
                        suspicious_files.append(analysis)
                        self._update_auth_results(f"   🚨 {verdict} (Score: {score}/100) [{processing_mode}]\n")
                        
                        # Détails des problèmes détectés
                        if analysis['duration_analysis']['suspicious']:
                            self._update_auth_results(f"      ⏱️ {analysis['duration_analysis']['reason']}\n")
                        
                        if analysis['filename_analysis']['suspicious']:
                            self._update_auth_results(f"      📝 {analysis['filename_analysis']['reason']}\n")
                        
                        if analysis['technical_analysis']['suspicious']:
                            self._update_auth_results(f"      🔧 {analysis['technical_analysis']['reason']}\n")
                        
                        if analysis['metadata_analysis']['suspicious']:
                            self._update_auth_results(f"      📋 {analysis['metadata_analysis']['reason']}\n")
                    else:
                        self._update_auth_results(f"   ✅ {verdict} (Score: {score}/100) [{processing_mode}]\n")
                    
                    self._update_auth_results("\n")
                    processed_count += 1
                    
                except Exception as e:
                    self._update_auth_results(f"   ❌ Erreur de traitement détaillée: {str(e)}\n")
                    
                    # Essayer une approche de fallback plus simple avec mutagen seul
                    try:
                        self._update_auth_results(f"   🔄 Mode mutagen uniquement...\n")
                        
                        import mutagen
                        
                        # Analyse avec mutagen uniquement
                        metadata_basic = {
                            'title': '',
                            'artist': '',
                            'album': '',
                            'year': None,
                            'bitrate': 0,
                            'format': Path(file_path).suffix.lower(),
                            'sample_rate': 44100,  # Valeur par défaut
                            'channels': 2,  # Valeur par défaut
                            'musicbrainz_id': None,
                            'isrc': None,
                            'album_artist': None
                        }
                        
                        # Lire le fichier avec mutagen
                        audio_file = mutagen.File(file_path)
                        if audio_file:
                            # Durée du fichier
                            actual_duration = getattr(audio_file.info, 'length', 0)
                            
                            # Propriétés audio
                            metadata_basic['bitrate'] = getattr(audio_file.info, 'bitrate', 0) // 1000  # Convertir en kbps
                            metadata_basic['sample_rate'] = getattr(audio_file.info, 'sample_rate', 44100)
                            metadata_basic['channels'] = getattr(audio_file.info, 'channels', 2)
                            
                            # Extraire les métadonnées si disponibles
                            if hasattr(audio_file, 'tags') and audio_file.tags:
                                tags = audio_file.tags
                                
                                # Titre (différents formats)
                                for title_key in ['TIT2', 'TITLE', '\xa9nam', 'Title']:
                                    if title_key in tags:
                                        metadata_basic['title'] = str(tags[title_key][0])
                                        break
                                
                                # Artiste
                                for artist_key in ['TPE1', 'ARTIST', '\xa9ART', 'Artist']:
                                    if artist_key in tags:
                                        metadata_basic['artist'] = str(tags[artist_key][0])
                                        break
                                
                                # Album
                                for album_key in ['TALB', 'ALBUM', '\xa9alb', 'Album']:
                                    if album_key in tags:
                                        metadata_basic['album'] = str(tags[album_key][0])
                                        break
                                
                                # Année
                                for year_key in ['TDRC', 'DATE', '\xa9day', 'Year']:
                                    if year_key in tags:
                                        try:
                                            year_str = str(tags[year_key][0])
                                            # Extraire juste l'année (format YYYY-MM-DD -> YYYY)
                                            metadata_basic['year'] = int(year_str[:4])
                                            break
                                        except:
                                            pass
                        else:
                            actual_duration = 0
                        
                        # Durée de référence = durée actuelle pour éviter les faux positifs
                        reference_duration = actual_duration
                        
                        processing_mode = "Mutagen seul"
                        
                        # Lancer l'analyse d'authenticité avec données simplifiées
                        analysis = detector.full_analysis(
                            file_path=file_path,
                            actual_duration=actual_duration,
                            reference_duration=reference_duration,
                            metadata=metadata_basic
                        )
                        
                        # Afficher les résultats
                        score = analysis['suspicion_score']
                        verdict = analysis['verdict_text']
                        
                        if score >= 15:  # Fichier suspect
                            suspicious_files.append(analysis)
                            self._update_auth_results(f"   🚨 {verdict} (Score: {score}/100) [Mode simplifié]\n")
                            
                            # Détails des problèmes détectés
                            if analysis['duration_analysis']['suspicious']:
                                self._update_auth_results(f"      ⏱️ {analysis['duration_analysis']['reason']}\n")
                            
                            if analysis['filename_analysis']['suspicious']:
                                self._update_auth_results(f"      📝 {analysis['filename_analysis']['reason']}\n")
                            
                            if analysis['technical_analysis']['suspicious']:
                                self._update_auth_results(f"      🔧 {analysis['technical_analysis']['reason']}\n")
                            
                            if analysis['metadata_analysis']['suspicious']:
                                self._update_auth_results(f"      📋 {analysis['metadata_analysis']['reason']}\n")
                        else:
                            self._update_auth_results(f"   ✅ {verdict} (Score: {score}/100) [Mode simplifié]\n")
                        
                        self._update_auth_results("\n")
                        processed_count += 1
                        
                    except Exception as fallback_error:
                        self._update_auth_results(f"   💥 Erreur de fallback: {str(fallback_error)}\n")
                        self._update_auth_results("   ⏭️ Fichier ignoré\n\n")
                        continue
            
            # Résumé final
            self._update_auth_results("=" * 60 + "\n")
            self._update_auth_results("📊 RÉSUMÉ DE LA DÉTECTION\n")
            self._update_auth_results("=" * 60 + "\n")
            self._update_auth_results(f"Fichiers analysés: {processed_count}/{total_files}\n")
            self._update_auth_results(f"Fichiers suspects: {len(suspicious_files)}\n")
            
            if len(suspicious_files) > 0:
                self._update_auth_results(f"Taux de suspicion: {len(suspicious_files)/processed_count*100:.1f}%\n\n")
                
                # Générer les rapports
                output_dir = os.path.join(directory, "authenticity_reports")
                reports = detector.generate_report(output_dir)
                
                self._update_auth_results("📄 RAPPORTS GÉNÉRÉS:\n")
                for report_type, path in reports.items():
                    self._update_auth_results(f"   • {report_type}: {path}\n")
            else:
                self._update_auth_results("🎉 Aucun fichier suspect détecté!\n")
            
            self._update_auth_results(f"\n✅ Détection terminée avec succès!")
            
        except Exception as e:
            self._update_auth_results(f"❌ Erreur lors de la détection: {str(e)}\n")
            self.log(f"❌ Erreur de détection d'authenticité: {e}", "ERROR")
    
    def _update_auth_results(self, text):
        """Met à jour le texte des résultats d'authenticité"""
        def update():
            self.auth_results_text.config(state='normal')
            self.auth_results_text.insert(tk.END, text)
            self.auth_results_text.see(tk.END)
            self.auth_results_text.config(state='disabled')
        
        # Exécuter dans le thread principal
        self.root.after(0, update)
    
    def show_authenticity_results(self):
        """Affiche les derniers résultats de détection d'authenticité"""
        directory = self.selected_directory.get()
        if not directory:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un répertoire")
            return
        
        # Chercher les rapports dans le répertoire
        reports_dir = os.path.join(directory, "authenticity_reports")
        
        if not os.path.exists(reports_dir):
            messagebox.showinfo("Information", "Aucun rapport de détection trouvé. Lancez d'abord une analyse.")
            return
        
        # Trouver le rapport TXT le plus récent
        txt_files = [f for f in os.listdir(reports_dir) if f.startswith("non_original_summary_") and f.endswith(".txt")]
        
        if not txt_files:
            messagebox.showinfo("Information", "Aucun rapport texte trouvé.")
            return
        
        # Prendre le plus récent
        latest_report = max(txt_files, key=lambda f: os.path.getctime(os.path.join(reports_dir, f)))
        report_path = os.path.join(reports_dir, latest_report)
        
        # Lire et afficher le rapport
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # Créer une nouvelle fenêtre pour afficher le rapport
            report_window = tk.Toplevel(self.root)
            report_window.title("📊 Rapport de Détection d'Authenticité")
            report_window.geometry("800x600")
            
            # Zone de texte avec scrollbar
            text_frame = ttk.Frame(report_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            report_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
            report_text.pack(fill=tk.BOTH, expand=True)
            
            # Insérer le contenu du rapport
            report_text.insert(tk.END, report_content)
            report_text.config(state='disabled')
            
            # Bouton pour ouvrir le dossier des rapports
            button_frame = ttk.Frame(report_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            ttk.Button(
                button_frame, 
                text="📁 Ouvrir le dossier des rapports", 
                command=lambda: os.startfile(reports_dir)
            ).pack(side=tk.LEFT)
            
            ttk.Button(
                button_frame, 
                text="🔄 Actualiser", 
                command=report_window.destroy
            ).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire le rapport: {e}")
    
    def create_organization_tab(self, notebook):
        """Crée l'onglet d'organisation"""
        org_frame = ttk.Frame(notebook)
        notebook.add(org_frame, text="📁 Organisation")
        
        # Pattern de nommage
        pattern_frame = ttk.LabelFrame(org_frame, text="🏷️ Pattern de nommage")
        pattern_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.naming_pattern = tk.StringVar(value="{artist}/{album}/{track:02d} - {title}")
        ttk.Label(pattern_frame, text="Pattern:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        ttk.Entry(pattern_frame, textvariable=self.naming_pattern, width=50).pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Label(pattern_frame, text="Variables disponibles: {artist}, {album}, {title}, {year}, {track}, {genre}").pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        # Aperçu de l'organisation
        preview_frame = ttk.LabelFrame(org_frame, text="👀 Aperçu")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bouton pour générer l'aperçu
        ttk.Button(preview_frame, text="🔄 Générer aperçu", command=self.generate_preview).pack(pady=5)
    
    def select_directory(self):
        """Sélectionne le répertoire à analyser"""
        directory = filedialog.askdirectory(title="Sélectionner le répertoire musical")
        if directory:
            self.selected_directory.set(directory)
            self.scan_directory_info()
    
    def select_output_directory(self):
        """Sélectionne le répertoire de sortie"""
        directory = filedialog.askdirectory(title="Sélectionner le répertoire de sortie")
        if directory:
            self.output_directory.set(directory)
    
    def scan_directory_info(self):
        """Scanne et affiche les informations sur le répertoire sélectionné"""
        directory = self.selected_directory.get()
        if not directory or not os.path.exists(directory):
            return
        
        audio_files = []
        total_files = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                total_files += 1
                file_path = os.path.join(root, file)
                if is_audio_file(file_path):
                    audio_files.append(file_path)
        
        info = f"📂 Répertoire: {directory}\n"
        info += f"📄 Total fichiers: {total_files}\n"
        info += f"🎵 Fichiers audio: {len(audio_files)}\n"
        info += f"📊 Types détectés: "
        
        extensions = {}
        for file in audio_files:
            ext = os.path.splitext(file)[1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
        
        info += ", ".join([f"{ext}({count})" for ext, count in extensions.items()])
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)
    
    def log(self, message, level="INFO"):
        """Ajoute un message au log"""
        self.log_queue.put((message, level))
    
    def check_log_queue(self):
        """Vérifie et traite les messages en attente dans la queue"""
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                timestamp = time.strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] {message}\n"
                
                self.log_text.insert(tk.END, formatted_message, level)
                self.log_text.see(tk.END)
                
        except queue.Empty:
            pass
        
        # Programmer la prochaine vérification
        self.root.after(100, self.check_log_queue)
    
    def clear_logs(self):
        """Efface la console de logs"""
        self.log_text.delete(1.0, tk.END)
    
    def initialize_components(self):
        """Initialise les composants avec la configuration actuelle"""
        try:
            config = {
                'output_directory': self.output_directory.get(),
                'create_year_folders': self.create_year_folders.get(),
                'naming_pattern': self.naming_pattern.get(),
                'move_files': self.move_files.get(),
                'dry_run': self.dry_run.get()
            }
            
            self.metadata_manager = MetadataManager()
            self.file_organizer = FileOrganizer(config)
            self.fingerprinter = AudioFingerprinter(self.api_key.get())
            
            self.log("✅ Composants initialisés avec succès", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"❌ Erreur d'initialisation: {str(e)}", "ERROR")
            return False
    
    def start_analysis(self):
        """Démarre l'analyse en arrière-plan"""
        if not self.selected_directory.get():
            messagebox.showerror("Erreur", "Veuillez sélectionner un répertoire")
            return
        
        if not self.initialize_components():
            return
        
        # Lancer l'analyse dans un thread séparé
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
    
    def run_analysis(self):
        """Exécute l'analyse des fichiers"""
        try:
            directory = self.selected_directory.get()
            api_key = self.api_key.get()
            
            if not api_key:
                self.log("❌ Clé API AcoustID manquante", "ERROR")
                return
                
            self.log(f"🔍 Début de l'analyse de {directory}", "INFO")
            
            # Collecter et filtrer les fichiers audio
            all_audio_files = []
            filtered_audio_files = []
            min_size = self.min_file_size.get()
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        all_audio_files.append(file_path)
                        
                        # Appliquer les filtres
                        try:
                            file_size = os.path.getsize(file_path)
                            if file_size < min_size:
                                self.log(f"⚠️ Fichier trop petit ignoré: {os.path.basename(file_path)} ({file_size} bytes)", "WARNING")
                                continue
                            
                            # Vérifier que le fichier est accessible
                            if not os.access(file_path, os.R_OK):
                                self.log(f"⚠️ Fichier non accessible ignoré: {os.path.basename(file_path)}", "WARNING")
                                continue
                            
                            filtered_audio_files.append(file_path)
                            
                        except Exception as e:
                            self.log(f"⚠️ Erreur lors du filtrage de {os.path.basename(file_path)}: {e}", "WARNING")
            
            self.log(f"📄 {len(all_audio_files)} fichiers audio trouvés, {len(filtered_audio_files)} après filtrage", "INFO")
            
            if not filtered_audio_files:
                self.log("⚠️ Aucun fichier audio trouvé dans le répertoire", "WARNING")
                return
            
            # Initialiser l'AudioFingerprinter
            fingerprinter = AudioFingerprinter(api_key)
            
            # Analyser chaque fichier
            max_files = len(filtered_audio_files)  # Traiter tous les fichiers
            results = []
            
            for i, file_path in enumerate(filtered_audio_files[:max_files]):
                self.progress_var.set(f"Analyse {i+1}/{max_files}")
                self.progress_bar['value'] = (i+1) / max_files * 100
                
                try:
                    self.log(f"🎵 Traitement: {os.path.basename(file_path)}", "INFO")
                    
                    # Analyser le fichier avec l'AudioFingerprinter
                    result = fingerprinter.resolve_metadata(file_path)
                    
                    if result['status'] == 'acoustid_success':
                        metadata = result['updates']
                        self.log(f"✅ {metadata.get('artist', 'Inconnu')} - {metadata.get('title', 'Inconnu')}", "SUCCESS")
                        
                        results.append({
                            'file': file_path,
                            'metadata': metadata,
                            'status': 'success',
                            'confidence': result.get('confidence', 0)
                        })
                        
                    elif result['status'] == 'musicbrainz_success':
                        metadata = result['updates']
                        self.log(f"🎼 MusicBrainz: {metadata.get('artist', 'Inconnu')} - {metadata.get('title', 'Inconnu')}", "SUCCESS")
                        
                        results.append({
                            'file': file_path,
                            'metadata': metadata,
                            'status': 'success',
                            'confidence': result.get('confidence', 0),
                            'source': 'musicbrainz'
                        })
                        
                    elif result['status'] == 'spectral_success':
                        metadata = result['updates']
                        self.log(f"🔄 Méthode spectrale: {metadata.get('artist', 'Inconnu')} - {metadata.get('title', 'Inconnu')}", "INFO")
                        
                        results.append({
                            'file': file_path,
                            'metadata': metadata,
                            'status': 'spectral',
                            'similarity': result.get('similarity', 0)
                        })
                        
                    elif result['status'] == 'manual_review':
                        # Afficher des informations détaillées pour la révision manuelle
                        filename = os.path.basename(file_path)
                        reason = result.get('reason', 'Confiance insuffisante')
                        confidence = result.get('confidence', 0)
                        
                        # Message principal
                        self.log(f"⚠️ Révision manuelle: {filename}", "WARNING")
                        self.log(f"   └─ Raison: {reason}", "INFO")
                        
                        # Détails supplémentaires si disponibles
                        if result.get('details'):
                            self.log(f"   └─ Détails: {result['details']}", "INFO")
                        
                        # NOUVEAU: Afficher les suggestions MusicBrainz si disponibles
                        if result.get('musicbrainz_suggestions'):
                            mb_data = result['musicbrainz_suggestions']
                            mb_confidence = mb_data.get('confidence', 0)
                            recording = mb_data.get('recording', {})
                            
                            artist = recording.get('artist-credit-phrase', 'Artiste inconnu')
                            title = recording.get('title', 'Titre inconnu')
                            
                            self.log(f"   🎼 Suggestion MusicBrainz ({mb_confidence:.1%}): {artist} - {title}", "INFO")
                        
                        # Afficher les suggestions d'action
                        if result.get('suggested_actions'):
                            self.log(f"   └─ Actions suggérées:", "INFO")
                            for i, action in enumerate(result['suggested_actions'][:2], 1):  # Limiter à 2 actions
                                self.log(f"      {i}. {action}", "INFO")
                        
                        # Données AcoustID disponibles pour inspection
                        acoustid_data = result.get('acoustid_data')
                        if acoustid_data and acoustid_data.get('metadata'):
                            metadata = acoustid_data['metadata']
                            suggested_artist = metadata.get('artists', [{}])[0].get('name', 'Inconnu') if metadata.get('artists') else 'Inconnu'
                            suggested_title = metadata.get('title', 'Inconnu')
                            self.log(f"   └─ Suggestion AcoustID: {suggested_artist} - {suggested_title} ({confidence:.1%})", "INFO")
                        
                        results.append({
                            'file': file_path,
                            'status': 'manual_review',
                            'reason': reason,
                            'details': result.get('details', ''),
                            'suggested_actions': result.get('suggested_actions', []),
                            'acoustid_suggestion': acoustid_data.get('metadata') if acoustid_data else None,
                            'acoustid_data': result.get('acoustid_data'),  # Données AcoustID complètes
                            'musicbrainz_suggestions': result.get('musicbrainz_suggestions'),  # CORRECTION: Ajouter les suggestions MusicBrainz !
                            'confidence': confidence
                        })
                        
                    else:  # failed
                        self.log(f"❌ Échec: {result.get('error', 'Erreur inconnue')}", "ERROR")
                        results.append({
                            'file': file_path,
                            'status': 'error',
                            'error': result.get('error', 'Erreur inconnue')
                        })
                    
                except Exception as e:
                    # Utiliser le gestionnaire d'erreurs centralisé
                    error_result = self.error_manager.handle_error(
                        e, 
                        {'file_path': file_path, 'operation': 'analysis'}
                    )
                    
                    # Logger selon la sévérité déterminée par le gestionnaire
                    if error_result['severity'] == 'warning':
                        self.log(f"⚠️ {error_result['user_message']}", "WARNING")
                    else:
                        self.log(f"❌ {error_result['user_message']}", "ERROR")
                    
                    results.append({
                        'file': file_path,
                        'status': 'error',
                        'error': error_result['user_message'],
                        'error_code': error_result['error_code']
                    })
            
            # Résumé des résultats avec détails
            success_count = len([r for r in results if r['status'] == 'success'])
            spectral_count = len([r for r in results if r['status'] == 'spectral'])
            manual_count = len([r for r in results if r['status'] == 'manual_review'])
            error_count = len([r for r in results if r['status'] == 'error'])
            
            # Compter les types d'erreurs
            corrupt_count = len([r for r in results if r['status'] == 'error' and 'corrompu' in r.get('error', '')])
            format_count = len([r for r in results if r['status'] == 'error' and 'supporté' in r.get('error', '')])
            
            self.progress_var.set("Analyse terminée")
            summary = f"🎯 Analyse terminée: {success_count} réussis, {spectral_count} spectraux, {manual_count} manuels, {error_count} erreurs"
            if corrupt_count > 0:
                summary += f" ({corrupt_count} corrompus)"
            if format_count > 0:
                summary += f" ({format_count} format non supporté)"
            
            self.log(summary, "SUCCESS")
            
            # Sauvegarder les résultats pour la révision manuelle
            self.last_analysis_results = results
            
            # Charger automatiquement les fichiers en révision manuelle si il y en a
            manual_files = [r for r in results if r.get('status') == 'manual_review']
            if manual_files:
                self.log(f"🔄 Chargement automatique de {len(manual_files)} fichiers en révision manuelle", "INFO")
                try:
                    self.load_manual_review_files()
                except Exception as e:
                    self.log(f"⚠️ Erreur lors du chargement automatique: {e}", "WARNING")
            
        except Exception as e:
            self.log(f"💥 Erreur critique: {str(e)}", "ERROR")
    
    def start_organization(self):
        """Démarre l'organisation des fichiers"""
        if not self.organize_files.get():
            messagebox.showwarning("Attention", "L'option 'Organiser les fichiers' doit être activée")
            return
        
        if not self.selected_directory.get():
            messagebox.showerror("Erreur", "Veuillez sélectionner un répertoire")
            return
        
        if not self.initialize_components():
            return
        
        # Lancer l'organisation dans un thread séparé
        thread = threading.Thread(target=self.run_organization)
        thread.daemon = True
        thread.start()
    
    def run_organization(self):
        """Exécute l'organisation des fichiers"""
        try:
            directory = self.selected_directory.get()
            api_key = self.api_key.get()
            
            if not api_key:
                self.log("❌ Clé API AcoustID manquante", "ERROR")
                return
                
            self.log("📁 Début de l'organisation", "INFO")
            
            # Collecter les fichiers audio
            audio_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        audio_files.append(file_path)
            
            if not audio_files:
                self.log("⚠️ Aucun fichier audio trouvé", "WARNING")
                return
            
            # Initialiser les composants
            fingerprinter = AudioFingerprinter(api_key)
            
            # Traiter les fichiers (limiter à 5 pour éviter les quotas API)
            max_files = min(5, len(audio_files))
            organized_count = 0
            
            for i, file_path in enumerate(audio_files[:max_files]):
                self.progress_var.set(f"Organisation {i+1}/{max_files}")
                self.progress_bar['value'] = (i+1) / max_files * 100
                
                try:
                    self.log(f"🎵 Traitement: {os.path.basename(file_path)}", "INFO")
                    
                    # Analyser le fichier pour obtenir les métadonnées
                    result = fingerprinter.resolve_metadata(file_path)
                    
                    if result['status'] in ['acoustid_success', 'spectral_success', 'musicbrainz_success']:
                        metadata = result['updates']
                        
                        # Organiser le fichier
                        org_result = self.file_organizer.organize_file(file_path, metadata)
                        
                        if org_result['status'] == 'dry_run':
                            self.log(f"🔄 Simulation: {os.path.basename(file_path)} -> {org_result['destination']}", "INFO")
                            organized_count += 1
                        elif org_result['status'] == 'success':
                            self.log(f"✅ Organisé: {os.path.basename(file_path)} -> {org_result['destination']}", "SUCCESS")
                            organized_count += 1
                        else:
                            self.log(f"❌ Erreur d'organisation: {org_result.get('error', 'Inconnue')}", "ERROR")
                    
                    elif result['status'] == 'manual_review':
                        self.log(f"⚠️ Fichier ignoré (révision manuelle requise): {os.path.basename(file_path)}", "WARNING")
                    
                    else:
                        self.log(f"❌ Fichier ignoré (erreur d'analyse): {os.path.basename(file_path)}", "ERROR")
                        
                except Exception as e:
                    self.log(f"❌ Erreur critique: {str(e)}", "ERROR")
            
            # Statistiques finales
            stats = self.file_organizer.get_stats()
            self.log(f"📊 Statistiques: {stats}", "INFO")
            self.log(f"🎯 Organisation terminée: {organized_count} fichiers traités", "SUCCESS")
            
        except Exception as e:
            self.log(f"💥 Erreur d'organisation: {str(e)}", "ERROR")
    
    def generate_preview(self):
        """Génère un aperçu de l'organisation avec les vrais fichiers du dossier source"""
        if not self.initialize_components():
            return
        
        # Vérifier qu'un répertoire source est sélectionné
        source_directory = self.selected_directory.get()
        if not source_directory or not os.path.exists(source_directory):
            preview = "⚠️ Aucun répertoire source sélectionné ou répertoire inexistant.\n"
            preview += "Veuillez sélectionner un répertoire valide dans l'onglet Configuration.\n"
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, preview)
            return
        
        preview = "📁 Aperçu de l'organisation avec vos fichiers réels:\n\n"
        preview += f"Répertoire source: {source_directory}\n"
        preview += f"Répertoire de destination: {self.output_directory.get()}\n"
        preview += f"Pattern: {self.naming_pattern.get()}\n"
        preview += f"Dossiers par année: {'Oui' if self.create_year_folders.get() else 'Non'}\n\n"
        
        try:
            # Collecter les fichiers audio réels
            audio_files = []
            for root, dirs, files in os.walk(source_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_audio_file(file_path):
                        audio_files.append(file_path)
                        if len(audio_files) >= 5:  # Limiter à 5 fichiers pour l'aperçu
                            break
                if len(audio_files) >= 5:
                    break
            
            if not audio_files:
                preview += "⚠️ Aucun fichier audio trouvé dans le répertoire source.\n"
                preview += "Vérifiez que le répertoire contient des fichiers .mp3, .flac, .wav, etc.\n"
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, preview)
                return
            
            preview += f"📊 {len(audio_files)} fichier(s) trouvé(s) pour l'aperçu:\n\n"
            
            # Analyser chaque fichier et générer l'aperçu d'organisation
            for i, file_path in enumerate(audio_files, 1):
                filename = os.path.basename(file_path)
                preview += f"{i}. 🎵 {filename}\n"
                
                try:
                    # Essayer d'obtenir les métadonnées existantes du fichier
                    from organizer.metadata_manager import MetadataManager
                    metadata_manager = MetadataManager()
                    
                    # Extraire les métadonnées du fichier (tags existants)
                    metadata = metadata_manager.extract_metadata(file_path)
                    
                    # Si pas de métadonnées, créer un exemple basé sur le nom de fichier
                    if not metadata or not any([metadata.get('artist'), metadata.get('title')]):
                        # Essayer d'extraire des infos du nom de fichier
                        metadata = self._extract_metadata_from_filename(filename)
                    
                    # Générer le chemin de destination
                    result_path = self.file_organizer._build_destination_path(file_path, metadata)
                    
                    # Afficher les métadonnées trouvées
                    artist = metadata.get('artist', 'Artiste Inconnu')
                    title = metadata.get('title', 'Titre Inconnu')
                    album = metadata.get('album', 'Album Inconnu')
                    
                    preview += f"   ├─ Artiste: {artist}\n"
                    preview += f"   ├─ Titre: {title}\n"
                    preview += f"   ├─ Album: {album}\n"
                    preview += f"   └─ 📂 Destination: {result_path}\n\n"
                    
                except Exception as e:
                    preview += f"   └─ ❌ Erreur lors de l'analyse: {str(e)}\n\n"
            
            # Ajouter des conseils
            preview += "💡 Conseils:\n"
            preview += "• Si les métadonnées semblent incorrectes, lancez d'abord une analyse pour les améliorer\n"
            preview += "• Ajustez le pattern de nommage si nécessaire\n"
            preview += "• Activez 'Mode simulation' pour tester sans déplacer les fichiers\n"
            
        except Exception as e:
            preview += f"❌ Erreur lors de la génération de l'aperçu: {str(e)}\n"
            preview += "Vérifiez que le répertoire source est accessible.\n"
        
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, preview)
    
    def _extract_metadata_from_filename(self, filename):
        """Extrait des métadonnées basiques du nom de fichier"""
        # Supprimer l'extension
        name = os.path.splitext(filename)[0]
        
        import re
        
        # Extraire d'abord le numéro de track si présent
        track_number = 1
        track_match = re.match(r'^(\d+)\.?\s*', name)
        if track_match:
            track_number = int(track_match.group(1))
        
        # Patterns courants pour extraire artiste et titre (ordre d'importance)
        patterns = [
            r'^\d+\s*-\s*(.+?)\s*-\s*(.+)$',  # "02 - Artiste - Titre"
            r'^\d+\.?\s*(.+?)\s*-\s*(.+)$',  # "01. Artiste - Titre" ou "01 Artiste - Titre"
            r'^(.+?)\s*-\s*(.+)$',  # "Artiste - Titre"
            r'^(.+?)_(.+)$',  # "Artiste_Titre"
            r'^(.+?)\s+(.+)$',  # "Artiste Titre" (avec espace)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    artist = groups[0].strip()
                    title = groups[1].strip()
                    
                    return {
                        'artist': artist,
                        'title': title,
                        'album': 'Album Inconnu',
                        'track_number': track_number
                    }
        
        # Si aucun pattern ne correspond, utiliser le nom complet comme titre
        return {
            'artist': 'Artiste Inconnu',
            'title': name,
            'album': 'Album Inconnu',
            'track_number': 1
        }

    def load_settings(self):
        """Charge les paramètres sauvegardés depuis le fichier JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Charger les paramètres avec des valeurs par défaut
                self.selected_directory.set(settings.get('selected_directory', ''))
                self.api_key.set(settings.get('api_key', 'votre_api_key'))
                self.output_directory.set(settings.get('output_directory', './organized_music'))
                
                print(f"💾 Paramètres chargés depuis {self.config_file}")
                
        except Exception as e:
            print(f"⚠️ Impossible de charger les paramètres: {e}")
            # Utiliser les valeurs par défaut (déjà définies)

    def save_settings(self):
        """Sauvegarde les paramètres actuels dans le fichier JSON"""
        try:
            # Créer le répertoire config s'il n'existe pas
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            settings = {
                'selected_directory': self.selected_directory.get(),
                'api_key': self.api_key.get(),
                'output_directory': self.output_directory.get(),
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
        # Sauvegarder une dernière fois les paramètres
        self.save_settings()
        # Fermer l'application
        self.root.destroy()

def main():
    """Point d'entrée principal"""
    root = tk.Tk()
    app = MusicFolderManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
