# spectral_analyzer.py
import wave
import numpy as np
import struct
import os
import subprocess
import tempfile
from pathlib import Path

class SpectralMatcher:
    def __init__(self, threshold=0.7):
        self.threshold = threshold
        
    def _extract_features(self, file_path):
        """Extraction de caractéristiques audio avec support multi-format complet"""
        try:
            # Détecter le format du fichier
            file_ext = Path(file_path).suffix.lower()
            print(f"   📀 Format détecté: {file_ext}")
            
            # Stratégie 1: Pour WAV, essayer d'abord ffmpeg puis native en fallback
            if file_ext == '.wav':
                print(f"   🔄 Utilisation ffmpeg pour WAV (meilleur support 24-bit)")
                ffmpeg_result = self._extract_features_ffmpeg(file_path)
                if ffmpeg_result:
                    return ffmpeg_result
                
                print(f"   🎵 Fallback vers extraction native WAV")
                return self._extract_features_wav(file_path)
            
            # Stratégie 2: Utiliser ffmpeg pour tous les autres formats
            print(f"   🔄 Tentative conversion ffmpeg pour {file_ext}")
            ffmpeg_result = self._extract_features_ffmpeg(file_path)
            if ffmpeg_result:
                return ffmpeg_result
            
            # Stratégie 3: Fallback avec mutagen pour infos basiques
            print(f"   ⚠️ Utilisation fallback mutagen")
            return self._extract_features_fallback(file_path)
            
        except Exception as e:
            print(f"Erreur extraction features: {e}")
            return self._extract_features_fallback(file_path)
    
    def _extract_features_wav(self, file_path):
        """Extraction native pour fichiers WAV avec gestion robuste"""
        try:
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                # Vérification de la cohérence des données
                if len(frames) == 0:
                    print(f"   ⚠️ Fichier WAV vide")
                    return None
                
                # Calcul de la taille attendue
                expected_bytes_per_sample = sample_width * channels
                if len(frames) % expected_bytes_per_sample != 0:
                    print(f"   ⚠️ Taille de buffer WAV incohérente")
                    return None
                
                # Conversion en array numpy selon la profondeur
                try:
                    if sample_width == 1:
                        data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
                        data = (data - 128) / 128.0  # Conversion 8-bit vers float
                    elif sample_width == 2:
                        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                        data = data / 32768.0  # Conversion 16-bit vers float
                    elif sample_width == 3:
                        # 24-bit (plus rare)
                        print(f"   ⚠️ WAV 24-bit détecté")
                        return None
                    else:
                        data = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
                        data = data / 2147483648.0  # Conversion 32-bit vers float
                except ValueError as e:
                    print(f"   ⚠️ Erreur parsing WAV buffer: {e}")
                    return None
                
                # Si stéréo ou multi-canal, moyenne des canaux
                if channels > 1:
                    try:
                        data = data.reshape(-1, channels).mean(axis=1)
                    except ValueError:
                        print(f"   ⚠️ Erreur reshape multi-canal")
                        return None
                
                return self._calculate_audio_features(data, sample_rate, 'wav_native')
                
        except wave.Error as e:
            print(f"   ⚠️ Erreur format WAV: {e}")
            return None
        except Exception as e:
            print(f"   ⚠️ Erreur extraction WAV: {e}")
            return None
    
    def _extract_features_ffmpeg(self, file_path):
        """Extraction avec ffmpeg pour tous formats (MP3, FLAC, OGG, AIFF, etc.)"""
        try:
            # Créer un fichier temporaire WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
            
            try:
                # Chercher ffmpeg dans plusieurs emplacements
                ffmpeg_paths = [
                    Path(__file__).parent / "audio_tools" / "ffmpeg.exe",
                    "ffmpeg",  # System PATH
                    "ffmpeg.exe"
                ]
                
                ffmpeg_cmd = None
                for path in ffmpeg_paths:
                    try:
                        if isinstance(path, Path) and path.exists():
                            ffmpeg_cmd = str(path)
                            break
                        elif isinstance(path, str):
                            subprocess.run([path, "-version"], capture_output=True, timeout=5)
                            ffmpeg_cmd = path
                            break
                    except:
                        continue
                
                if not ffmpeg_cmd:
                    print("   ⚠️ ffmpeg non trouvé, utilisation du fallback")
                    return None
                
                # Convertir avec ffmpeg - optimisé pour tous formats
                cmd = [
                    ffmpeg_cmd,
                    "-i", file_path,
                    "-ac", "1",  # mono
                    "-ar", "22050",  # 22kHz suffisant pour analyse
                    "-t", "30",  # 30 secondes max pour analyse rapide
                    "-f", "wav",  # Force format WAV
                    "-acodec", "pcm_s16le",  # PCM 16-bit
                    "-y",  # overwrite
                    temp_wav_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                
                if result.returncode != 0:
                    print(f"   ⚠️ Échec ffmpeg: {result.stderr.decode()[:100]}")
                    return None
                
                # Analyser le WAV temporaire
                return self._extract_features_wav(temp_wav_path)
                    
            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Erreur extraction ffmpeg: {e}")
            return None
    
    def _calculate_audio_features(self, data, sample_rate, source_format):
        """Calcule les caractéristiques audio avancées à partir des données"""
        try:
            # Normalisation sécurisée
            if np.max(np.abs(data)) > 0:
                data = data.astype(np.float32) / np.max(np.abs(data))
            else:
                data = data.astype(np.float32)
            
            # Analyser seulement les premières secondes pour la performance
            analysis_length = min(len(data), sample_rate * 15)  # 15 secondes max
            data_analysis = data[:analysis_length]
            
            # Calcul FFT pour analyse spectrale
            if len(data_analysis) > 0:
                fft = np.fft.fft(data_analysis)
                spectrum = np.abs(fft)[:len(fft)//2]
                freqs = np.fft.fftfreq(len(data_analysis), 1/sample_rate)[:len(spectrum)]
            else:
                spectrum = np.array([0])
                freqs = np.array([0])
            
            # Caractéristiques audio avancées
            features = {
                'energy': float(np.mean(data_analysis**2)) if len(data_analysis) > 0 else 0.0,
                'zero_crossings': int(np.sum(np.diff(np.sign(data_analysis)) != 0)) if len(data_analysis) > 1 else 0,
                'spectral_centroid': float(np.sum(spectrum * freqs) / np.sum(spectrum)) if np.sum(spectrum) > 0 else 0.0,
                'spectral_rolloff': float(freqs[np.where(np.cumsum(spectrum) >= 0.85 * np.sum(spectrum))[0][0]]) if len(spectrum) > 0 and len(np.where(np.cumsum(spectrum) >= 0.85 * np.sum(spectrum))[0]) > 0 else 0.0,
                'spectral_bandwidth': float(np.sqrt(np.sum(((freqs - np.sum(spectrum * freqs) / np.sum(spectrum))**2) * spectrum) / np.sum(spectrum))) if np.sum(spectrum) > 0 else 0.0,
                'rms_energy': float(np.sqrt(np.mean(data_analysis**2))) if len(data_analysis) > 0 else 0.0,
                'spectral_flux': float(np.mean(np.diff(spectrum)**2)) if len(spectrum) > 1 else 0.0,
                'sample_rate': sample_rate,
                'duration': len(data) / sample_rate,
                'format': source_format,
                'analysis_length': analysis_length,
                'peak_frequency': float(freqs[np.argmax(spectrum)]) if len(spectrum) > 0 else 0.0,
                'low_energy': float(np.mean(spectrum[:len(spectrum)//4])) if len(spectrum) > 4 else 0.0,
                'mid_energy': float(np.mean(spectrum[len(spectrum)//4:3*len(spectrum)//4])) if len(spectrum) > 4 else 0.0,
                'high_energy': float(np.mean(spectrum[3*len(spectrum)//4:])) if len(spectrum) > 4 else 0.0
            }
            
            return features
            
        except Exception as e:
            print(f"Erreur calcul features: {e}")
            return None
    
    def _extract_features_fallback(self, file_path):
        """Fallback utilisant mutagen pour extraire des features basiques"""
        try:
            from mutagen import File
            
            audio_file = File(file_path)
            if audio_file is None:
                return None
            
            # Extraire des caractéristiques basiques des métadonnées
            info = audio_file.info
            
            features = {
                'energy': 0.5,  # Valeur par défaut
                'zero_crossings': 1000,  # Valeur par défaut
                'spectral_centroid': 2000.0,  # Valeur par défaut
                'spectral_rolloff': 8000,  # Valeur par défaut
                'sample_rate': getattr(info, 'sample_rate', 44100),
                'duration': getattr(info, 'length', 0),
                'bitrate': getattr(info, 'bitrate', 0),
                'format': 'mutagen_fallback'
            }
            
            return features
            
        except Exception as e:
            print(f"Erreur extraction features fallback: {e}")
            return None
    
    def compare(self, file1, file2):
        """Calcule la similarité spectrale entre 2 fichiers"""
        try:
            features1 = self._extract_features(file1)
            features2 = self._extract_features(file2)
            
            if not features1 or not features2:
                return 0.0
            
            # Clés numériques pour la comparaison (exclure les chaînes)
            numeric_keys = ['energy', 'zero_crossings', 'spectral_centroid', 
                          'spectral_rolloff', 'spectral_bandwidth', 'rms_energy',
                          'spectral_flux', 'sample_rate', 'duration', 'analysis_length',
                          'peak_frequency', 'low_energy', 'mid_energy', 'high_energy']
            
            # Similarité basée sur les caractéristiques numériques
            similarities = []
            for key in numeric_keys:
                if key in features1 and key in features2:
                    try:
                        val1, val2 = float(features1[key]), float(features2[key])
                        if val1 != 0 and val2 != 0:
                            sim = 1 - abs(val1 - val2) / max(abs(val1), abs(val2))
                            similarities.append(max(0, float(sim)))
                    except (ValueError, TypeError):
                        # Ignorer les valeurs non numériques
                        continue
            
            # Convertir en float pour éviter les erreurs numpy
            result = float(np.mean(similarities)) if similarities else 0.0
            return result
            
        except Exception as e:
            print(f"Erreur comparaison spectrale: {e}")
            return 0.0

    def is_match(self, reference_db, unknown_file):
        """Vérification contre une base de références"""
        try:
            for ref_path, ref_id in reference_db.items():
                similarity = self.compare(ref_path, unknown_file)
                if similarity > self.threshold:
                    return ref_id, similarity
            return None, 0
        except Exception as e:
            print(f"Erreur matching: {e}")
            return None, 0
