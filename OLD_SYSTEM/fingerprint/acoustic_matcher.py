#!/usr/bin/env python3
"""
Module pour la génération et comparaison de fingerprints acoustiques
Utilise fpcalc pour générer les fingerprints AcoustID
"""

import subprocess
import os
import logging
from pathlib import Path

class AcousticMatcher:
    def __init__(self, fpcalc_path=None):
        self.logger = logging.getLogger(__name__)
        
        # Trouver fpcalc
        if fpcalc_path:
            self.fpcalc_path = fpcalc_path
        else:
            # Chercher dans le dossier audio_tools
            project_root = Path(__file__).parent.parent
            self.fpcalc_path = project_root / "audio_tools" / "fpcalc.exe"
        
        if not os.path.exists(self.fpcalc_path):
            self.logger.warning(f"fpcalc non trouvé à {self.fpcalc_path}")
            self.fpcalc_path = None
    
    def generate_fingerprint(self, file_path):
        """Génère un fingerprint acoustique pour un fichier audio"""
        if not self.fpcalc_path:
            self.logger.error("fpcalc non disponible")
            return None
        
        try:
            # Commande fpcalc
            cmd = [str(self.fpcalc_path), "-length", "120", file_path]
            
            self.logger.debug(f"Exécution de fpcalc: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"Erreur fpcalc: {result.stderr}")
                return None
            
            # Parser la sortie
            lines = result.stdout.strip().split('\n')
            fingerprint_data = {}
            
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'DURATION':
                        fingerprint_data['duration'] = float(value)
                    elif key == 'FINGERPRINT':
                        fingerprint_data['fingerprint'] = value
            
            if 'fingerprint' not in fingerprint_data:
                self.logger.error("Pas de fingerprint dans la sortie fpcalc")
                return None
            
            self.logger.debug(f"Fingerprint généré: {len(fingerprint_data['fingerprint'])} caractères")
            return fingerprint_data
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout lors de la génération du fingerprint pour {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du fingerprint: {e}")
            return None
    
    def compare_fingerprints(self, fp1, fp2):
        """Compare deux fingerprints (implémentation basique)"""
        if not fp1 or not fp2:
            return 0.0
        
        # Comparaison simple (à améliorer)
        if fp1 == fp2:
            return 1.0
        
        # Calcul de similitude basique
        common_chars = sum(1 for a, b in zip(fp1, fp2) if a == b)
        max_len = max(len(fp1), len(fp2))
        
        return common_chars / max_len if max_len > 0 else 0.0