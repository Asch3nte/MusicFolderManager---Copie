#!/usr/bin/env python3
"""
Module pour la génération et comparaison de fingerprints acoustiques
Utilise fpcalc pour générer les fingerprints AcoustID
"""

import subprocess
import os
import logging
import re
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
    
    def clean_fingerprint(self, fingerprint):
        """Nettoie un fingerprint pour AcoustID avec correction du padding Base64"""
        if not fingerprint:
            return fingerprint
        
        # Supprimer les espaces et retours à la ligne
        cleaned = fingerprint.strip()
        
        # Supprimer les caractères invisibles (garder seulement ASCII imprimables)
        cleaned = re.sub(r'[^\x20-\x7E]', '', cleaned)
        
        # Garder seulement les caractères Base64 valides
        base64_pattern = r'[A-Za-z0-9+/=]'
        cleaned = ''.join(re.findall(base64_pattern, cleaned))
        
        # CORRECTION CRITIQUE: Fixer le padding Base64
        # Supprimer tout padding existant
        cleaned = cleaned.rstrip('=')
        
        # Ajouter le bon padding Base64
        padding_needed = (4 - len(cleaned) % 4) % 4
        cleaned += '=' * padding_needed
        
        # Vérifier que le Base64 est maintenant valide
        try:
            import base64
            base64.b64decode(cleaned)
            self.logger.debug(f"✅ Fingerprint Base64 valide après correction")
        except Exception as e:
            self.logger.warning(f"⚠️ Fingerprint toujours invalide après correction: {e}")
        
        if len(cleaned) != len(fingerprint):
            self.logger.warning(f"Fingerprint nettoyé: {len(fingerprint)} -> {len(cleaned)} caractères")
        
        return cleaned
    
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
                line = line.strip()  # Nettoyer les espaces et retours à la ligne
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == 'DURATION':
                        fingerprint_data['duration'] = float(value)
                    elif key == 'FINGERPRINT':
                        # Nettoyer le fingerprint avant de le stocker
                        raw_fingerprint = value
                        cleaned_fingerprint = self.clean_fingerprint(raw_fingerprint)
                        fingerprint_data['fingerprint'] = cleaned_fingerprint
                        fingerprint_data['raw_fingerprint'] = raw_fingerprint  # Garder l'original pour debug
            
            if 'fingerprint' not in fingerprint_data:
                self.logger.error("Pas de fingerprint dans la sortie fpcalc")
                return None
            
            self.logger.debug(f"Fingerprint généré: {len(fingerprint_data['fingerprint'])} caractères (nettoyé)")
            if 'raw_fingerprint' in fingerprint_data:
                self.logger.debug(f"Fingerprint brut: {len(fingerprint_data['raw_fingerprint'])} caractères")
            
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