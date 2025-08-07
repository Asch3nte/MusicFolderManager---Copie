import os
import hashlib

def get_file_fingerprint(file_path):
    """Crée un hash unique pour le fichier"""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def is_audio_file(file_path):
    """Vérifie si un fichier est un fichier audio supporté"""
    # Extensions audio supportées (liste étendue)
    extensions = [
        # Formats compressés
        '.mp3', '.aac', '.m4a', '.ogg', '.oga', '.opus', '.wma',
        # Formats non compressés
        '.wav', '.flac', '.aiff', '.aif', '.au', '.snd',
        # Formats mobiles et streaming
        '.3gp', '.3g2', '.amr', '.awb',
        # Formats spécialisés
        '.dsd', '.dsf', '.dff', '.ape', '.wv', '.tta', '.mka',
        # Formats rares mais supportés par certains outils
        '.ra', '.rm', '.ac3', '.dts', '.mpc', '.mp+', '.mpp'
    ]
    
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext in extensions
