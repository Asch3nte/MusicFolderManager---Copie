"""
Interface utilisateur complète pour Enhanced Music Manager
Version 2 : Avec analyse de fichiers
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import threading
import os
from pathlib import Path
from typing import List


class MusicManagerGUI:
    """Interface utilisateur avec analyse de fichiers"""
    
    def __init__(self):
        """Initialise l'interface utilisateur"""
        print("🎵 Création de l'interface Music Manager v2...")
        
        # Interface graphique principale
        self.root = tk.Tk()
        self.root.title("🎵 Enhanced Music Manager v2")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Variables de l'interface
        self.api_key = tk.StringVar()
        self.source_directory = tk.StringVar()
        
        # Seuils de confiance
        self.acoustid_threshold = tk.DoubleVar(value=0.85)
        self.musicbrainz_threshold = tk.DoubleVar(value=0.70)
        self.spectral_threshold = tk.DoubleVar(value=0.70)
        
        # Variables pour l'analyse
        self.current_files = []
        self.analysis_results = []
        self.is_analyzing = False
        
        # Configuration
        self.config_file = Path("config/ui_settings_v2.json")
        
        # Charger les paramètres
        self.load_settings()
        
        # Créer l'interface
        self.setup_ui()
        
        # Configurer la fermeture
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        
        # === TITRE PRINCIPAL ===
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(title_frame, text="🎵 Enhanced Music Manager v2", 
                 font=('Arial', 20, 'bold')).pack()
        ttk.Label(title_frame, text="Analyse et organisation automatique de votre musique", 
                 font=('Arial', 12)).pack()
        
        # === ONGLETS ===
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
    
    def setup_config_tab(self, parent):
        """Onglet de configuration"""
        
        # === CONFIGURATION API ===
        api_group = ttk.LabelFrame(parent, text="🔑 Configuration API AcoustID", padding=15)
        api_group.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(api_group, text="Clé API AcoustID:").pack(anchor='w')
        api_entry = ttk.Entry(api_group, textvariable=self.api_key, width=60, show='*')
        api_entry.pack(fill='x', pady=5)
        
        ttk.Button(api_group, text="💾 Sauvegarder Clé API", 
                  command=self.save_api_key).pack(anchor='w')
        
        # === SÉLECTION DE RÉPERTOIRE ===
        dir_group = ttk.LabelFrame(parent, text="📁 Répertoire Musical", padding=15)
        dir_group.pack(fill='x', padx=10, pady=10)
        
        dir_frame = ttk.Frame(dir_group)
        dir_frame.pack(fill='x')
        
        ttk.Entry(dir_frame, textvariable=self.source_directory, 
                 state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(dir_frame, text="📂 Parcourir", 
                  command=self.select_directory).pack(side='right', padx=(5,0))
        
        # === SEUILS DE CONFIANCE ===
        thresholds_group = ttk.LabelFrame(parent, text="🎯 Seuils de Confiance", padding=15)
        thresholds_group.pack(fill='x', padx=10, pady=10)
        
        # Variables pour labels dynamiques
        self.acoustid_label = tk.StringVar()
        self.spectral_label = tk.StringVar()
        self.musicbrainz_label = tk.StringVar()
        self.update_threshold_labels()
        
        # AcoustID
        ttk.Label(thresholds_group, textvariable=self.acoustid_label).pack(anchor='w')
        acoustid_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                 variable=self.acoustid_threshold, orient='horizontal',
                                 command=self.on_acoustid_change)
        acoustid_scale.pack(fill='x', pady=2)
        
        # Spectral
        ttk.Label(thresholds_group, textvariable=self.spectral_label).pack(anchor='w')
        spectral_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                 variable=self.spectral_threshold, orient='horizontal',
                                 command=self.on_spectral_change)
        spectral_scale.pack(fill='x', pady=2)
        
        # MusicBrainz
        ttk.Label(thresholds_group, textvariable=self.musicbrainz_label).pack(anchor='w')
        musicbrainz_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                    variable=self.musicbrainz_threshold, orient='horizontal',
                                    command=self.on_musicbrainz_change)
        musicbrainz_scale.pack(fill='x', pady=2)
        
        # === BOUTONS D'ACTION ===
        actions_group = ttk.LabelFrame(parent, text="🚀 Actions", padding=15)
        actions_group.pack(fill='x', padx=10, pady=10)
        
        buttons_frame = ttk.Frame(actions_group)
        buttons_frame.pack(fill='x')
        
        ttk.Button(buttons_frame, text="💾 Sauvegarder Configuration", 
                  command=self.save_settings).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="🔄 Recharger Configuration", 
                  command=self.load_settings).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="🧪 Tester Configuration", 
                  command=self.test_configuration).pack(side='left', padx=5)
    
    def setup_analysis_tab(self, parent):
        """Onglet d'analyse avec scanner de fichiers"""
        
        # === SCANNER DE FICHIERS ===
        scanner_group = ttk.LabelFrame(parent, text="🔍 Scanner de Fichiers", padding=15)
        scanner_group.pack(fill='x', padx=10, pady=10)
        
        # Boutons de contrôle
        controls_frame = ttk.Frame(scanner_group)
        controls_frame.pack(fill='x', pady=(0,10))
        
        ttk.Button(controls_frame, text="🔍 Scanner Répertoire", 
                  command=self.scan_directory).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="🎵 Analyser Fichiers", 
                  command=self.start_analysis).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="🛑 Arrêter", 
                  command=self.stop_analysis).pack(side='left', padx=5)
        
        # === LISTE DES FICHIERS ===
        files_group = ttk.LabelFrame(parent, text="📁 Fichiers Audio Détectés", padding=15)
        files_group.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview pour les fichiers
        columns = ('Nom', 'Taille', 'Statut')
        self.files_tree = ttk.Treeview(files_group, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.files_tree.heading(col, text=col)
            self.files_tree.column(col, width=150)
        
        # Scrollbars
        files_scroll = ttk.Scrollbar(files_group, orient='vertical', command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=files_scroll.set)
        
        self.files_tree.pack(side='left', fill='both', expand=True)
        files_scroll.pack(side='right', fill='y')
        
        # === PROGRESSION ===
        progress_group = ttk.LabelFrame(parent, text="📊 Progression", padding=15)
        progress_group.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.StringVar(value="Prêt à analyser")
        ttk.Label(progress_group, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(progress_group, mode='determinate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Zone de statut
        self.status_text = tk.Text(progress_group, height=4, wrap='word')
        status_scroll = ttk.Scrollbar(progress_group, orient='vertical', command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scroll.set)
        
        self.status_text.pack(side='left', fill='both', expand=True)
        status_scroll.pack(side='right', fill='y')
    
    def setup_results_tab(self, parent):
        """Onglet résultats avec affichage détaillé"""
        
        # === RÉSULTATS D'ANALYSE ===
        results_group = ttk.LabelFrame(parent, text="📊 Résultats d'Analyse", padding=15)
        results_group.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Boutons d'export
        export_frame = ttk.Frame(results_group)
        export_frame.pack(fill='x', pady=(0,10))
        
        ttk.Button(export_frame, text="📄 Exporter JSON", 
                  command=self.export_json).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📊 Exporter CSV", 
                  command=self.export_csv).pack(side='left', padx=5)
        ttk.Button(export_frame, text="🧹 Vider Résultats", 
                  command=self.clear_results).pack(side='right', padx=5)
        
        # Treeview des résultats
        result_columns = ('Fichier', 'Statut', 'Artiste', 'Titre', 'Album', 'Confiance')
        self.results_tree = ttk.Treeview(results_group, columns=result_columns, show='headings', height=15)
        
        for col in result_columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=120)
        
        # Scrollbars pour résultats
        results_scroll = ttk.Scrollbar(results_group, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scroll.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scroll.pack(side='right', fill='y')
    
    # === MÉTHODES DE CALLBACK ===
    
    def on_acoustid_change(self, value):
        """Callback changement seuil AcoustID"""
        self.update_threshold_labels()
    
    def on_spectral_change(self, value):
        """Callback changement seuil Spectral"""
        self.update_threshold_labels()
    
    def on_musicbrainz_change(self, value):
        """Callback changement seuil MusicBrainz"""
        self.update_threshold_labels()
    
    def update_threshold_labels(self):
        """Met à jour les labels des seuils"""
        self.acoustid_label.set(f"🎧 AcoustID: {self.acoustid_threshold.get():.2f}")
        self.spectral_label.set(f"📊 Spectral: {self.spectral_threshold.get():.2f}")
        self.musicbrainz_label.set(f"🎼 MusicBrainz: {self.musicbrainz_threshold.get():.2f}")
    
    def save_api_key(self):
        """Sauvegarde la clé API"""
        if self.api_key.get().strip():
            self.save_settings()
            messagebox.showinfo("✅ Succès", "Clé API sauvegardée !")
        else:
            messagebox.showwarning("⚠️ Attention", "Veuillez entrer une clé API")
    
    def select_directory(self):
        """Sélectionne le répertoire source"""
        directory = filedialog.askdirectory(title="Sélectionner le répertoire musical")
        if directory:
            self.source_directory.set(directory)
            self.save_settings()
            # Vider la liste des fichiers précédents
            for item in self.files_tree.get_children():
                self.files_tree.delete(item)
            self.add_status("📁 Nouveau répertoire sélectionné")
    
    def test_configuration(self):
        """Teste la configuration actuelle"""
        errors = []
        
        if not self.api_key.get().strip():
            errors.append("• Clé API manquante")
        
        if not self.source_directory.get():
            errors.append("• Répertoire source non sélectionné")
        elif not Path(self.source_directory.get()).exists():
            errors.append("• Répertoire source introuvable")
        
        if errors:
            messagebox.showerror("❌ Configuration Incomplète", 
                               "Problèmes détectés:\\n" + "\\n".join(errors))
        else:
            messagebox.showinfo("✅ Configuration OK", 
                              "Configuration validée avec succès !")
    
    def scan_directory(self):
        """Scanne le répertoire pour les fichiers audio"""
        if not self.source_directory.get():
            messagebox.showwarning("⚠️ Attention", "Sélectionnez d'abord un répertoire")
            return
        
        def scan_worker():
            try:
                self.add_status("🔍 Scan du répertoire en cours...")
                directory = Path(self.source_directory.get())
                
                # Extensions audio supportées
                audio_extensions = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma'}
                
                files = []
                for ext in audio_extensions:
                    files.extend(directory.rglob(f"*{ext}"))
                    files.extend(directory.rglob(f"*{ext.upper()}"))
                
                # Mettre à jour l'interface dans le thread principal
                self.root.after(0, lambda: self.populate_files_list(files))
                
            except Exception as e:
                self.root.after(0, lambda: self.add_status(f"❌ Erreur scan: {e}"))
        
        threading.Thread(target=scan_worker, daemon=True).start()
    
    def populate_files_list(self, files: List[Path]):
        """Remplit la liste des fichiers détectés"""
        # Vider la liste actuelle
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        self.current_files = files
        
        for file_path in files:
            try:
                size = file_path.stat().st_size
                size_str = f"{size / 1024 / 1024:.1f} MB"
            except:
                size_str = "Inconnu"
            
            self.files_tree.insert('', 'end', values=(
                file_path.name,
                size_str,
                'En attente'
            ))
        
        self.add_status(f"📁 {len(files)} fichiers audio trouvés")
    
    def start_analysis(self):
        """Démarre l'analyse des fichiers"""
        if not self.current_files:
            messagebox.showwarning("⚠️ Attention", "Aucun fichier à analyser. Scannez d'abord un répertoire.")
            return
        
        if not self.api_key.get().strip():
            messagebox.showwarning("⚠️ Attention", "Configurez d'abord votre clé API")
            return
        
        self.is_analyzing = True
        self.progress_bar['maximum'] = len(self.current_files)
        self.progress_bar['value'] = 0
        
        def analysis_worker():
            try:
                for i, file_path in enumerate(self.current_files):
                    if not self.is_analyzing:
                        break
                    
                    # Simulation d'analyse (à remplacer par la vraie analyse)
                    self.root.after(0, lambda i=i, f=file_path: self.update_analysis_progress(i, f))
                    
                    # Simulation du temps d'analyse
                    threading.Event().wait(0.5)
                
                self.root.after(0, self.analysis_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self.add_status(f"❌ Erreur analyse: {e}"))
        
        threading.Thread(target=analysis_worker, daemon=True).start()
        self.add_status("🚀 Analyse démarrée...")
    
    def update_analysis_progress(self, index: int, file_path: Path):
        """Met à jour la progression de l'analyse"""
        self.progress_bar['value'] = index + 1
        self.progress_var.set(f"Analyse: {index + 1}/{len(self.current_files)} - {file_path.name}")
        
        # Mettre à jour le statut dans la liste
        items = self.files_tree.get_children()
        if index < len(items):
            current_values = list(self.files_tree.item(items[index])['values'])
            current_values[2] = '✅ Analysé'
            self.files_tree.item(items[index], values=current_values)
        
        # Simuler un résultat d'analyse
        result = {
            'file': file_path.name,
            'status': 'Succès',
            'artist': 'Artiste Exemple',
            'title': 'Titre Exemple',
            'album': 'Album Exemple',
            'confidence': 0.85
        }
        
        self.results_tree.insert('', 'end', values=(
            result['file'],
            result['status'],
            result['artist'],
            result['title'],
            result['album'],
            f"{result['confidence']:.2f}"
        ))
    
    def stop_analysis(self):
        """Arrête l'analyse en cours"""
        self.is_analyzing = False
        self.add_status("🛑 Analyse arrêtée par l'utilisateur")
    
    def analysis_complete(self):
        """Appelé quand l'analyse est terminée"""
        self.is_analyzing = False
        self.progress_var.set("✅ Analyse terminée")
        self.add_status("🎉 Analyse terminée avec succès !")
        messagebox.showinfo("🎉 Terminé", "Analyse terminée ! Consultez l'onglet Résultats.")
    
    def export_json(self):
        """Exporte les résultats en JSON"""
        messagebox.showinfo("📄 Export", "Export JSON - Fonctionnalité à implémenter")
    
    def export_csv(self):
        """Exporte les résultats en CSV"""
        messagebox.showinfo("📊 Export", "Export CSV - Fonctionnalité à implémenter")
    
    def clear_results(self):
        """Vide les résultats"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.add_status("🧹 Résultats vidés")
    
    def add_status(self, message: str):
        """Ajoute un message au statut"""
        self.status_text.insert('end', f"{message}\\n")
        self.status_text.see('end')
        self.root.update_idletasks()
    
    # === GESTION DES PARAMÈTRES ===
    
    def load_settings(self):
        """Charge les paramètres sauvegardés"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.api_key.set(settings.get('api_key', ''))
                self.source_directory.set(settings.get('source_directory', ''))
                self.acoustid_threshold.set(settings.get('acoustid_threshold', 0.85))
                self.musicbrainz_threshold.set(settings.get('musicbrainz_threshold', 0.70))
                self.spectral_threshold.set(settings.get('spectral_threshold', 0.70))
                
                self.update_threshold_labels()
                print(f"💾 Paramètres chargés depuis {self.config_file}")
        except Exception as e:
            print(f"⚠️ Erreur chargement paramètres: {e}")
    
    def save_settings(self):
        """Sauvegarde les paramètres actuels"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            settings = {
                'api_key': self.api_key.get(),
                'source_directory': self.source_directory.get(),
                'acoustid_threshold': self.acoustid_threshold.get(),
                'musicbrainz_threshold': self.musicbrainz_threshold.get(),
                'spectral_threshold': self.spectral_threshold.get()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Paramètres sauvegardés dans {self.config_file}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
    
    def on_closing(self):
        """Gestionnaire de fermeture"""
        self.is_analyzing = False
        self.save_settings()
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        print("🚀 Lancement de l'interface...")
        self.root.mainloop()


def main():
    """Point d'entrée principal"""
    print("🎵 Enhanced Music Manager - Interface v2")
    app = MusicManagerGUI()
    app.run()


if __name__ == "__main__":
    main()
