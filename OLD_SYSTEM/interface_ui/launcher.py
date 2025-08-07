#!/usr/bin/env python3
"""
Lanceur pour l'interface graphique de MusicFolderManager
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent.parent))

try:
    # Vérifier que tkinter est disponible
    import tkinter as tk
    
    # Importer l'interface
    from interface_ui.main_gui import MusicFolderManagerGUI
    
    def main():
        """Lance l'interface graphique"""
        print("🎵 Démarrage de MusicFolderManager GUI...")
        print("✨ NOUVEAU: Support multi-format + Cache intelligent!")
        print("🕵️ NOUVEAU: Détection d'authenticité des fichiers audio!")
        print("🎼 Formats supportés: WAV, MP3, FLAC, OGG, AIFF, M4A, WMA, OPUS, AC3, APE")
        print("💾 Cache SQLite: Fingerprints, spectres, métadonnées")
        print("🚀 Quotas API: Éliminés par cache intelligent")
        print("🔍 Analyse: Durée, technique, métadonnées (nom de fichier désactivé)")
        print()
        
        # Créer la fenêtre principale
        root = tk.Tk()
        
        # Configurer l'icône (optionnel)
        try:
            # Si vous avez un fichier .ico, décommentez la ligne suivante
            # root.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # Créer l'application
        app = MusicFolderManagerGUI(root)
        
        print("✅ Interface graphique prête!")
        print("🔄 Stratégie de traitement: Cache → Spectral → Acoustic → MusicBrainz")
        print("🛡️ Limite de 10 fichiers supprimée - Traitement complet activé")
        print("🕵️ Détection d'authenticité: Onglet Analyse → Détection d'Authenticité")
        print()
        
        # Lancer la boucle principale
        root.mainloop()
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assurez-vous que tous les modules nécessaires sont installés.")
    sys.exit(1)

except Exception as e:
    print(f"💥 Erreur inattendue: {e}")
    sys.exit(1)
