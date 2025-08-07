import os
import hashlib

def get_file_fingerprint(file_path):
    """Crée un hash unique pour le fichier"""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def is_audio_file(file_path):
    extensions = ['.mp3', '.flac', '.wav', '.ogg', '.m4a']
    return any(file_path.lower().endswith(ext) for ext in extensions)
