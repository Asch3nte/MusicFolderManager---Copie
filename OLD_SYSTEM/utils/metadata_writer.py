#!/usr/bin/env python3
"""
Module pour la gestion des métadonnées audio
Écriture et mise à jour des tags dans les fichiers audio
"""

import os
from pathlib import Path

# Import conditionnel de mutagen pour éviter les erreurs si non installé
try:
    from mutagen import File
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON, TPE2, TPUB, TXXX, UFID, TPE2, TPUB, TXXX, UFID
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

class MetadataWriter:
    """Gestionnaire d'écriture des métadonnées audio"""
    
    def __init__(self, logger=None):
        self.logger = logger
        
        if not MUTAGEN_AVAILABLE:
            self.log("⚠️ Mutagen non disponible - les métadonnées ne seront pas appliquées", "WARNING")
        
    def log(self, message, level="INFO"):
        """Helper pour le logging"""
        if self.logger:
            if level == "ERROR":
                self.logger.error(message)
            elif level == "WARNING":
                self.logger.warning(message)
            elif level == "SUCCESS":
                self.logger.info(f"✅ {message}")
            else:
                self.logger.info(message)
        else:
            print(f"[{level}] {message}")
    
    def apply_metadata(self, file_path, metadata_dict):
        """
        Applique les métadonnées à un fichier audio
        
        Args:
            file_path (str): Chemin vers le fichier audio
            metadata_dict (dict): Dictionnaire des métadonnées {
                'artist': str,
                'title': str, 
                'album': str,
                'year': str/int,
                'track': str/int,
                'genre': str
            }
        
        Returns:
            bool: True si succès, False sinon
        """
        if not MUTAGEN_AVAILABLE:
            self.log(f"❌ Impossible d'appliquer les métadonnées (mutagen manquant): {os.path.basename(file_path)}", "ERROR")
            return False
        
        try:
            if not os.path.exists(file_path):
                self.log(f"Fichier introuvable: {file_path}", "ERROR")
                return False
            
            # Charger le fichier avec mutagen
            audio_file = File(file_path)
            
            if audio_file is None:
                self.log(f"Format audio non supporté: {file_path}", "ERROR")
                return False
            
            # Appliquer selon le format
            success = False
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in ['.mp3']:
                success = self._apply_mp3_metadata(audio_file, metadata_dict)
            elif file_ext in ['.m4a', '.mp4', '.m4p']:
                success = self._apply_mp4_metadata(audio_file, metadata_dict)
            elif file_ext in ['.flac']:
                success = self._apply_flac_metadata(audio_file, metadata_dict)
            elif file_ext in ['.ogg', '.oga']:
                success = self._apply_ogg_metadata(audio_file, metadata_dict)
            else:
                self.log(f"Format non supporté pour l'écriture: {file_ext}", "ERROR")
                return False
            
            if success:
                # Sauvegarder les modifications
                audio_file.save()
                self.log(f"Métadonnées appliquées avec succès: {os.path.basename(file_path)}", "SUCCESS")
                
                # Vérification post-écriture (debug)
                self._verify_written_metadata(file_path, metadata_dict)
                
                return True
            else:
                self.log(f"Erreur lors de l'application des métadonnées: {file_path}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erreur lors de l'écriture des métadonnées pour {file_path}: {e}", "ERROR")
            return False
    
    def _apply_mp3_metadata(self, audio_file, metadata_dict):
        """Applique les métadonnées pour les fichiers MP3"""
        try:
            # S'assurer qu'on a des tags ID3
            if audio_file.tags is None:
                audio_file.add_tags()
            
            tags = audio_file.tags
            
            # Appliquer chaque métadonnée (supprimer les anciennes avant d'ajouter)
            if metadata_dict.get('title'):
                tags.delall('TIT2')  # Supprimer les anciens titres
                tags.add(TIT2(encoding=3, text=metadata_dict['title']))
            
            if metadata_dict.get('artist'):
                tags.delall('TPE1')  # Supprimer les anciens artistes
                tags.add(TPE1(encoding=3, text=metadata_dict['artist']))
            
            if metadata_dict.get('album'):
                tags.delall('TALB')  # Supprimer les anciens albums
                tags.add(TALB(encoding=3, text=metadata_dict['album']))
            
            if metadata_dict.get('albumartist'):
                tags.delall('TPE2')  # Album artist
                tags.add(TPE2(encoding=3, text=metadata_dict['albumartist']))
            
            if metadata_dict.get('year'):
                year = str(metadata_dict['year'])
                tags.delall('TDRC')  # Supprimer les anciennes dates
                tags.add(TDRC(encoding=3, text=year))
            
            if metadata_dict.get('track'):
                track = str(metadata_dict['track'])
                tags.delall('TRCK')  # Supprimer les anciens numéros de piste
                tags.add(TRCK(encoding=3, text=track))
            
            if metadata_dict.get('genre'):
                tags.delall('TCON')  # Supprimer les anciens genres
                tags.add(TCON(encoding=3, text=metadata_dict['genre']))
            
            if metadata_dict.get('label'):
                tags.delall('TPUB')  # Publisher/Label
                tags.add(TPUB(encoding=3, text=metadata_dict['label']))
            
            if metadata_dict.get('catalognumber'):
                tags.delall('TXXX:CATALOGNUMBER')  # Custom tag pour catalog number
                tags.add(TXXX(encoding=3, desc='CATALOGNUMBER', text=metadata_dict['catalognumber']))
            
            if metadata_dict.get('musicbrainz_trackid'):
                tags.delall('UFID:http://musicbrainz.org')  # MusicBrainz Track ID
                tags.add(UFID(owner='http://musicbrainz.org', data=metadata_dict['musicbrainz_trackid'].encode()))
            
            if metadata_dict.get('musicbrainz_albumid'):
                tags.delall('TXXX:MusicBrainz Album Id')
                tags.add(TXXX(encoding=3, desc='MusicBrainz Album Id', text=metadata_dict['musicbrainz_albumid']))
            
            return True
            
        except Exception as e:
            self.log(f"Erreur MP3: {e}", "ERROR")
            return False
    
    def _apply_mp4_metadata(self, audio_file, metadata_dict):
        """Applique les métadonnées pour les fichiers MP4/M4A"""
        try:
            if metadata_dict.get('title'):
                audio_file['\xa9nam'] = metadata_dict['title']
            
            if metadata_dict.get('artist'):
                audio_file['\xa9ART'] = metadata_dict['artist']
            
            if metadata_dict.get('album'):
                audio_file['\xa9alb'] = metadata_dict['album']
            
            if metadata_dict.get('albumartist'):
                audio_file['aART'] = metadata_dict['albumartist']
            
            if metadata_dict.get('year'):
                audio_file['\xa9day'] = str(metadata_dict['year'])
            
            if metadata_dict.get('track'):
                audio_file['trkn'] = [(int(metadata_dict['track']), 0)]
            
            if metadata_dict.get('genre'):
                audio_file['\xa9gen'] = metadata_dict['genre']
            
            if metadata_dict.get('label'):
                audio_file['\xa9pub'] = metadata_dict['label']  # Publisher/Label
            
            if metadata_dict.get('catalognumber'):
                audio_file['----:com.apple.iTunes:CATALOGNUMBER'] = metadata_dict['catalognumber'].encode('utf-8')
            
            if metadata_dict.get('musicbrainz_trackid'):
                audio_file['----:com.apple.iTunes:MusicBrainz Track Id'] = metadata_dict['musicbrainz_trackid'].encode('utf-8')
            
            if metadata_dict.get('musicbrainz_albumid'):
                audio_file['----:com.apple.iTunes:MusicBrainz Album Id'] = metadata_dict['musicbrainz_albumid'].encode('utf-8')
            
            return True
            
        except Exception as e:
            self.log(f"Erreur MP4: {e}", "ERROR")
            return False
    
    def _apply_flac_metadata(self, audio_file, metadata_dict):
        """Applique les métadonnées pour les fichiers FLAC"""
        try:
            if metadata_dict.get('title'):
                audio_file['TITLE'] = metadata_dict['title']
            
            if metadata_dict.get('artist'):
                audio_file['ARTIST'] = metadata_dict['artist']
            
            if metadata_dict.get('album'):
                audio_file['ALBUM'] = metadata_dict['album']
            
            if metadata_dict.get('albumartist'):
                audio_file['ALBUMARTIST'] = metadata_dict['albumartist']
            
            if metadata_dict.get('year'):
                audio_file['DATE'] = str(metadata_dict['year'])
            
            if metadata_dict.get('track'):
                audio_file['TRACKNUMBER'] = str(metadata_dict['track'])
            
            if metadata_dict.get('genre'):
                audio_file['GENRE'] = metadata_dict['genre']
            
            if metadata_dict.get('label'):
                audio_file['LABEL'] = metadata_dict['label']
            
            if metadata_dict.get('catalognumber'):
                audio_file['CATALOGNUMBER'] = metadata_dict['catalognumber']
            
            if metadata_dict.get('musicbrainz_trackid'):
                audio_file['MUSICBRAINZ_TRACKID'] = metadata_dict['musicbrainz_trackid']
            
            if metadata_dict.get('musicbrainz_albumid'):
                audio_file['MUSICBRAINZ_ALBUMID'] = metadata_dict['musicbrainz_albumid']
            
            return True
            
        except Exception as e:
            self.log(f"Erreur FLAC: {e}", "ERROR")
            return False
    
    def _apply_ogg_metadata(self, audio_file, metadata_dict):
        """Applique les métadonnées pour les fichiers OGG"""
        try:
            if metadata_dict.get('title'):
                audio_file['TITLE'] = metadata_dict['title']
            
            if metadata_dict.get('artist'):
                audio_file['ARTIST'] = metadata_dict['artist']
            
            if metadata_dict.get('album'):
                audio_file['ALBUM'] = metadata_dict['album']
            
            if metadata_dict.get('albumartist'):
                audio_file['ALBUMARTIST'] = metadata_dict['albumartist']
            
            if metadata_dict.get('year'):
                audio_file['DATE'] = str(metadata_dict['year'])
            
            if metadata_dict.get('track'):
                audio_file['TRACKNUMBER'] = str(metadata_dict['track'])
            
            if metadata_dict.get('genre'):
                audio_file['GENRE'] = metadata_dict['genre']
            
            if metadata_dict.get('label'):
                audio_file['LABEL'] = metadata_dict['label']
            
            if metadata_dict.get('catalognumber'):
                audio_file['CATALOGNUMBER'] = metadata_dict['catalognumber']
            
            if metadata_dict.get('musicbrainz_trackid'):
                audio_file['MUSICBRAINZ_TRACKID'] = metadata_dict['musicbrainz_trackid']
            
            if metadata_dict.get('musicbrainz_albumid'):
                audio_file['MUSICBRAINZ_ALBUMID'] = metadata_dict['musicbrainz_albumid']
            
            return True
            
        except Exception as e:
            self.log(f"Erreur OGG: {e}", "ERROR")
            return False
    
    def format_musicbrainz_metadata(self, suggestion_data):
        """
        Convertit les données MusicBrainz en dictionnaire de métadonnées enrichi
        
        Args:
            suggestion_data (dict): Données de suggestion MusicBrainz (différents formats possibles)
        
        Returns:
            dict: Métadonnées formatées avec toutes les données disponibles
        """
        try:
            # DEBUG: Voir le format des données reçues
            self.log(f"🔍 DEBUG format_musicbrainz_metadata: {list(suggestion_data.keys())}", "DEBUG")
            
            # Gérer différents formats de données MusicBrainz
            recording = None
            
            # Format 1: {'recording': {...}} (depuis search_by_metadata)
            if 'recording' in suggestion_data:
                recording = suggestion_data['recording']
            
            # Format 2: Directement les données recording (depuis l'interface manuelle)
            elif 'title' in suggestion_data and 'artist-credit' in suggestion_data:
                recording = suggestion_data
            
            # Format 3: Via best_match
            elif 'best_match' in suggestion_data and 'recording' in suggestion_data['best_match']:
                recording = suggestion_data['best_match']['recording']
            
            # Format 4: Données déjà formatées depuis l'interface
            elif all(key in suggestion_data for key in ['artist', 'title']):
                # Les données sont déjà formatées, retourner telles quelles
                return suggestion_data
            
            if not recording:
                self.log("⚠️ Format de données MusicBrainz non reconnu", "WARNING")
                return {}
            
            # Extraire l'artiste (track artist)
            artist = 'Artiste Inconnu'
            if 'artist-credit' in recording:
                artists = []
                for credit in recording['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                if artists:
                    artist = ', '.join(artists)
            
            # Extraire le titre
            title = recording.get('title', 'Titre Inconnu')
            
            # Données de base
            metadata = {
                'artist': artist,
                'title': title
            }
            
            # Extraire les données de release (album)
            if 'release-list' in recording and recording['release-list']:
                release = recording['release-list'][0]  # Prendre le premier release
                
                # Album
                metadata['album'] = release.get('title', 'Album Inconnu')
                
                # Album Artist (peut être différent du track artist)
                if 'artist-credit' in release:
                    album_artists = []
                    for credit in release['artist-credit']:
                        if isinstance(credit, dict) and 'artist' in credit:
                            album_artists.append(credit['artist'].get('name', ''))
                    if album_artists:
                        metadata['albumartist'] = ', '.join(album_artists)
                
                # Année
                if 'date' in release:
                    try:
                        year = release['date'].split('-')[0]
                        metadata['year'] = int(year)
                    except:
                        pass
                
                # Label et numéro de catalogue
                if 'label-info-list' in release:
                    for label_info in release['label-info-list']:
                        if 'label' in label_info:
                            metadata['label'] = label_info['label'].get('name', '')
                        if 'catalog-number' in label_info:
                            metadata['catalognumber'] = label_info['catalog-number']
                        break  # Prendre le premier label
                
                # Track number dans le release
                if 'medium-list' in release:
                    for medium in release['medium-list']:
                        if 'track-list' in medium:
                            for i, track in enumerate(medium['track-list'], 1):
                                if track.get('recording', {}).get('id') == recording.get('id'):
                                    metadata['track'] = i
                                    break
                            if 'track' in metadata:
                                break
            
            # MusicBrainz IDs pour référence future
            metadata['musicbrainz_trackid'] = recording.get('id', '')
            if 'release-list' in recording and recording['release-list']:
                metadata['musicbrainz_albumid'] = recording['release-list'][0].get('id', '')
            
            return metadata
            
        except Exception as e:
            self.log(f"Erreur lors du formatage MusicBrainz: {e}", "ERROR")
            return {}

    def _verify_written_metadata(self, file_path, expected_metadata):
        """Vérifie que les métadonnées ont bien été écrites pour tous les formats"""
        try:
            from mutagen import File
            audio_file = File(file_path)
            if not audio_file:
                self.log(f"⚠️ Impossible de vérifier les métadonnées: {os.path.basename(file_path)}", "WARNING")
                return

            verification_log = []
            
            if file_path.lower().endswith('.mp3'):
                # Vérification MP3
                if expected_metadata.get('title'):
                    written = audio_file.tags.get('TIT2')
                    written_text = str(written.text[0]) if written and written.text else "VIDE"
                    verification_log.append(f"Titre: '{expected_metadata['title']}' → '{written_text}'")
                
                if expected_metadata.get('artist'):
                    written = audio_file.tags.get('TPE1')
                    written_text = str(written.text[0]) if written and written.text else "VIDE"
                    verification_log.append(f"Artiste: '{expected_metadata['artist']}' → '{written_text}'")
                
                if expected_metadata.get('albumartist'):
                    written = audio_file.tags.get('TPE2')
                    written_text = str(written.text[0]) if written and written.text else "VIDE"
                    verification_log.append(f"Album Artist: '{expected_metadata['albumartist']}' → '{written_text}'")
                    
            elif file_path.lower().endswith(('.m4a', '.mp4')):
                # Vérification MP4
                if expected_metadata.get('title'):
                    written = audio_file.tags.get('\xa9nam')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Titre: '{expected_metadata['title']}' → '{written_text}'")
                
                if expected_metadata.get('artist'):
                    written = audio_file.tags.get('\xa9ART')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Artiste: '{expected_metadata['artist']}' → '{written_text}'")
                
                if expected_metadata.get('albumartist'):
                    written = audio_file.tags.get('aART')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Album Artist: '{expected_metadata['albumartist']}' → '{written_text}'")
                    
            elif file_path.lower().endswith('.flac'):
                # Vérification FLAC
                if expected_metadata.get('title'):
                    written = audio_file.get('TITLE')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Titre: '{expected_metadata['title']}' → '{written_text}'")
                
                if expected_metadata.get('artist'):
                    written = audio_file.get('ARTIST')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Artiste: '{expected_metadata['artist']}' → '{written_text}'")
                
                if expected_metadata.get('albumartist'):
                    written = audio_file.get('ALBUMARTIST')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Album Artist: '{expected_metadata['albumartist']}' → '{written_text}'")
                    
            elif file_path.lower().endswith('.ogg'):
                # Vérification OGG
                if expected_metadata.get('title'):
                    written = audio_file.get('TITLE')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Titre: '{expected_metadata['title']}' → '{written_text}'")
                
                if expected_metadata.get('artist'):
                    written = audio_file.get('ARTIST')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Artiste: '{expected_metadata['artist']}' → '{written_text}'")
                
                if expected_metadata.get('albumartist'):
                    written = audio_file.get('ALBUMARTIST')
                    written_text = str(written[0]) if written else "VIDE"
                    verification_log.append(f"Album Artist: '{expected_metadata['albumartist']}' → '{written_text}'")

            # Log de la vérification
            if verification_log:
                self.log(f"🔍 Vérification métadonnées {os.path.basename(file_path)}:", "DEBUG")
                for line in verification_log[:3]:  # Limiter aux 3 premiers pour ne pas surcharger
                    self.log(f"   {line}", "DEBUG")
                    
        except Exception as e:
            self.log(f"Erreur lors de la vérification: {e}", "WARNING")
