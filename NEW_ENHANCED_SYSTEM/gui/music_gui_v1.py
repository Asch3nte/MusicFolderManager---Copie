"""
Interface utilisateur complète pour Enhanced Music Manager
Version 1 : Interface de base avec configuration
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from pathlib import Path


class MusicManagerGUI:
    """Interface utilisateur avec configuration de base"""
    
    def __init__(self):
        """Initialise l'interface utilisateur"""
        print("🎵 Création de l'interface Music Manager v1...")
        
        # Interface graphique principale
        self.root = tk.Tk()
        self.root.title("🎵 Enhanced Music Manager v1")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Variables de l'interface
        self.api_key = tk.StringVar()
        self.source_directory = tk.StringVar()
        
        # Seuils de confiance
        self.acoustid_threshold = tk.DoubleVar(value=0.85)
        self.musicbrainz_threshold = tk.DoubleVar(value=0.70)
        self.spectral_threshold = tk.DoubleVar(value=0.70)
        
        # Configuration
        self.config_file = Path("config/ui_settings_v1.json")
        
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
        
        ttk.Label(title_frame, text="🎵 Enhanced Music Manager", 
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
        
        # Onglet Analyse (placeholder)
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="🔍 Analyse")
        self.setup_analysis_tab(analysis_frame)
        
        # Onglet Résultats (placeholder)
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
        
        # AcoustID
        ttk.Label(thresholds_group, text=f"AcoustID: {self.acoustid_threshold.get():.2f}").pack(anchor='w')
        acoustid_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                 variable=self.acoustid_threshold, orient='horizontal')
        acoustid_scale.pack(fill='x', pady=2)
        
        # Spectral
        ttk.Label(thresholds_group, text=f"Spectral: {self.spectral_threshold.get():.2f}").pack(anchor='w')
        spectral_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                 variable=self.spectral_threshold, orient='horizontal')
        spectral_scale.pack(fill='x', pady=2)
        
        # MusicBrainz
        ttk.Label(thresholds_group, text=f"MusicBrainz: {self.musicbrainz_threshold.get():.2f}").pack(anchor='w')
        musicbrainz_scale = ttk.Scale(thresholds_group, from_=0.5, to=1.0, 
                                    variable=self.musicbrainz_threshold, orient='horizontal')
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
        """Onglet d'analyse - Version simple"""
        
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(info_frame, text="🔍 Analyse de Fichiers", 
                 font=('Arial', 16, 'bold')).pack(pady=20)
        
        ttk.Label(info_frame, text="Fonctionnalité en cours de développement...", 
                 font=('Arial', 12)).pack(pady=10)
        
        ttk.Label(info_frame, text="Configurez d'abord votre clé API et répertoire dans l'onglet Configuration", 
                 font=('Arial', 10), foreground='gray').pack(pady=5)
    
    def setup_results_tab(self, parent):
        """Onglet résultats - Version simple"""
        
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(info_frame, text="📊 Résultats d'Analyse", 
                 font=('Arial', 16, 'bold')).pack(pady=20)
        
        ttk.Label(info_frame, text="Les résultats apparaîtront ici après l'analyse...", 
                 font=('Arial', 12)).pack(pady=10)
    
    # === MÉTHODES DE CALLBACK ===
    
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
                               "Problèmes détectés:\n" + "\n".join(errors))
        else:
            messagebox.showinfo("✅ Configuration OK", 
                              "Configuration validée avec succès !")
    
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
        self.save_settings()
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        print("🚀 Lancement de l'interface...")
        self.root.mainloop()


def main():
    """Point d'entrée principal"""
    print("🎵 Enhanced Music Manager - Interface v1")
    app = MusicManagerGUI()
    app.run()


if __name__ == "__main__":
    main()
