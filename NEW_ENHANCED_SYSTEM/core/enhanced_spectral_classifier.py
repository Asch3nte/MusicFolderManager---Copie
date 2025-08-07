#!/usr/bin/env python3
"""
Analyse spectrale améliorée avec classification locale intelligente
"""

import logging
from typing import Dict, List, Optional, Any

class EnhancedSpectralClassifier:
    """Classificateur spectral amélioré avec analyse locale intelligente"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("🎼 Classificateur spectral amélioré initialisé")
    
    def classify_and_enhance(self, features: Dict[str, Any], metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """Classification spectrale intelligente avec analyse avancée"""
        try:
            self.logger.info("🎼 Analyse spectrale avancée...")
            
            # 1. Classification du genre musical
            detected_genre = self._classify_music_genre(features)
            
            # 2. Analyse de l'énergie et de la dynamique
            energy_profile = self._analyze_energy_profile(features)
            
            # 3. Classification du style et de l'époque
            style_analysis = self._analyze_musical_style(features)
            
            # 4. Calcul de confiance basé sur la qualité des caractéristiques
            confidence = self._calculate_spectral_confidence(features)
            
            # 5. Amélioration avec métadonnées si disponibles
            if metadata:
                confidence += 0.2  # Bonus pour métadonnées disponibles
                self.logger.info(f"📋 Métadonnées disponibles: {metadata.get('artist', 'N/A')} - {metadata.get('title', 'N/A')}")
            
            # Créer le résultat enrichi
            result = {
                'artist': metadata.get('artist', 'Artiste Inconnu') if metadata else 'Artiste Inconnu',
                'title': metadata.get('title', 'Titre Inconnu') if metadata else 'Titre Inconnu',
                'album': metadata.get('album', '') if metadata else '',
                'detected_genre': detected_genre,
                'energy_profile': energy_profile,
                'style_analysis': style_analysis,
                'spectral_quality': 'enhanced_local_analysis',
                'classification_details': {
                    'spectral_centroid': features.get('spectral_centroid', 0),
                    'energy': features.get('energy', 0),
                    'duration': features.get('duration', 0),
                    'sample_rate': features.get('sample_rate', 0)
                }
            }
            
            self.logger.info(f"🎵 Genre: {detected_genre}")
            self.logger.info(f"⚡ Profil énergétique: {energy_profile}")
            self.logger.info(f"🎨 Style: {style_analysis}")
            self.logger.info(f"📊 Confiance finale: {confidence:.2f}")
            
            return {
                'success': True,
                'confidence': min(confidence, 0.9),  # Max 0.9 pour analyse locale
                'method_used': 'enhanced_spectral_classification',
                'track_info': result,
                'all_results': [{'data': result, 'confidence': confidence}]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur classification spectrale: {e}")
            return {
                'success': False,
                'confidence': 0.0,
                'reason': f'classification_error: {str(e)}'
            }
    
    def _classify_music_genre(self, features: Dict[str, Any]) -> str:
        """Classification avancée du genre musical"""
        try:
            centroid = features.get('spectral_centroid', 0)
            energy = features.get('energy', 0)
            duration = features.get('duration', 0)
            rolloff = features.get('spectral_rolloff', 0)
            
            # Classification multi-critères
            if centroid > 4500 and energy > 0.6:
                return "rock/metal"
            elif centroid > 3500 and energy > 0.4 and duration < 240:
                return "pop/rock"
            elif centroid < 1500 and duration > 300:
                return "classical/orchestral"
            elif 1500 < centroid < 2500 and energy > 0.5:
                return "hip-hop/rap"
            elif rolloff > 8000 and energy > 0.3:
                return "electronic/dance"
            elif 2000 < centroid < 3000 and duration > 180:
                return "jazz/blues"
            elif centroid < 2000 and energy < 0.3:
                return "ambient/calm"
            elif duration > 300 and energy < 0.4:
                return "instrumental/soundtrack"
            else:
                return "pop/alternative"
                
        except Exception:
            return "unknown"
    
    def _analyze_energy_profile(self, features: Dict[str, Any]) -> str:
        """Analyse du profil énergétique"""
        try:
            energy = features.get('energy', 0)
            rms = features.get('rms_energy', 0)
            
            if energy > 0.7:
                return "très énergique"
            elif energy > 0.5:
                return "énergique"
            elif energy > 0.3:
                return "modéré"
            elif energy > 0.1:
                return "calme"
            else:
                return "très calme"
                
        except Exception:
            return "inconnu"
    
    def _analyze_musical_style(self, features: Dict[str, Any]) -> str:
        """Analyse du style musical"""
        try:
            centroid = features.get('spectral_centroid', 0)
            bandwidth = features.get('spectral_bandwidth', 0)
            duration = features.get('duration', 0)
            
            # Analyse du style basée sur les caractéristiques spectrales
            if centroid > 3000 and bandwidth > 1000:
                return "style moderne, production riche"
            elif centroid < 2000 and duration > 240:
                return "style traditionnel, arrangement classique"
            elif bandwidth > 1500:
                return "production complexe, multi-instrumentale"
            elif centroid > 2500 and duration < 180:
                return "format commercial, radio-friendly"
            else:
                return "style équilibré, production standard"
                
        except Exception:
            return "style indéterminé"
    
    def _calculate_spectral_confidence(self, features: Dict[str, Any]) -> float:
        """Calcul de confiance basé sur la qualité spectrale"""
        try:
            confidence = 0.3  # Base
            
            # Bonus pour durée appropriée
            duration = features.get('duration', 0)
            if duration > 30:
                confidence += 0.1
            if duration > 120:
                confidence += 0.1
                
            # Bonus pour qualité audio
            sample_rate = features.get('sample_rate', 0)
            if sample_rate >= 44100:
                confidence += 0.1
            if sample_rate >= 48000:
                confidence += 0.05
                
            # Bonus pour richesse spectrale
            centroid = features.get('spectral_centroid', 0)
            if centroid > 0:
                confidence += 0.1
                
            energy = features.get('energy', 0)
            if energy > 0:
                confidence += 0.1
                
            # Bonus pour cohérence des données
            if all(k in features for k in ['spectral_centroid', 'energy', 'duration']):
                confidence += 0.1
                
            return confidence
            
        except Exception:
            return 0.3