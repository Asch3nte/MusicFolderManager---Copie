#!/usr/bin/env python3
"""
🎵 ENHANCED MUSIC MANAGER - Point d'entrée principal
Système de gestion musicale moderne avec analyse AcoustID, spectrale et MusicBrainz
"""

import sys
import os
from pathlib import Path

# Ajouter le dossier du nouveau système au path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Point d'entrée principal"""
    try:
        # Import de l'interface complète depuis gui.py
        from gui.gui import CompleteMusicManagerGUI
        
        print("🎵 Lancement de Enhanced Music Manager...")
        print("📁 Système enhanced avec interface complète")
        print("🎵 Initialisation de l'interface Enhanced Music Manager...")
        print("🚀 Démarrage de l'interface complète...")
        
        # Créer et lancer l'interface
        app = CompleteMusicManagerGUI()
        app.run()
        
    except Exception as e:
        print(f"❌ Erreur interface complète: {e}")
        print("⚠️ Tentative avec interface de fallback...")
        
        try:
            from gui.complete_music_gui_simple import CompleteMusicManagerGUI
            print("🎵 Lancement de Enhanced Music Manager...")
            print("📁 Système enhanced avec interface simple")
            
            # Créer et lancer l'interface
            app = CompleteMusicManagerGUI()
            app.run()
            
        except Exception as e2:
            print(f"❌ Erreur fallback: {e2}")
            print("💡 Vérifiez que tous les modules sont correctement installés")
            sys.exit(1)

if __name__ == "__main__":
    main()
