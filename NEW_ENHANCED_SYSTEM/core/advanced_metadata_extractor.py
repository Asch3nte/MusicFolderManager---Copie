#!/usr/bin/env python3
"""
Extracteur de métadonnées avancé pour MusicFolderManager
Support complet des tags : album_artist, year, genre, style, track_number, etc.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

class AdvancedMetadataExtractor:
    """Extracteur avancé de métadonnées depuis les APIs musicales"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapping des champs standards
        self.field_mapping = {
            # Champs principaux
            'title': ['title', 'song', 'track'],
            'artist': ['artist', 'track_artist', 'performer'],
            'album_artist': ['album_artist', 'albumartist', 'album artist'],
            'album': ['album', 'release'],
            'year': ['year', 'date', 'release_date', 'originalyear'],
            'track_number': ['track', 'track_number', 'tracknumber', 'tracknum'],
            'total_tracks': ['total_tracks', 'totaltracks', 'track_total'],
            'disc_number': ['disc', 'disc_number', 'discnumber'],
            'total_discs': ['total_discs', 'totaldiscs', 'disc_total'],
            
            # Champs étendus
            'genre': ['genre', 'style', 'genres'],
            'style': ['style', 'substyle', 'styles'],
            'label': ['label', 'publisher', 'record_label'],
            'catalog_number': ['catalog', 'catalog_number', 'catalognumber'],
            'barcode': ['barcode', 'upc', 'ean'],
            'isrc': ['isrc'],
            'musicbrainz_id': ['musicbrainz_trackid', 'mb_trackid', 'mbid'],
            'musicbrainz_album_id': ['musicbrainz_albumid', 'mb_albumid'],
            'musicbrainz_artist_id': ['musicbrainz_artistid', 'mb_artistid'],
            
            # Informations techniques
            'duration': ['duration', 'length'],
            'bitrate': ['bitrate'],
            'sample_rate': ['sample_rate', 'samplerate'],
            'channels': ['channels'],
            'format': ['format', 'codec'],
            
            # Métadonnées étendues
            'country': ['country', 'release_country'],
            'language': ['language'],
            'mood': ['mood'],
            'tempo': ['tempo', 'bpm'],
            'key': ['key', 'initial_key'],
            'energy': ['energy'],
            'valence': ['valence', 'happiness'],
            'danceability': ['danceability'],
            'acousticness': ['acousticness'],
            'instrumentalness': ['instrumentalness'],
            'liveness': ['liveness'],
            'speechiness': ['speechiness']
        }
    
    def extract_from_musicbrainz(self, mb_data: Dict) -> Dict[str, Any]:
        """Extrait les métadonnées depuis une réponse MusicBrainz"""
        metadata = {}
        
        try:
            # Informations de base
            if 'recordings' in mb_data:
                recording = mb_data['recordings'][0] if mb_data['recordings'] else {}
                
                # Titre
                metadata['title'] = recording.get('title', '')
                
                # Durée (en millisecondes vers secondes)
                if 'length' in recording:
                    metadata['duration'] = recording['length'] / 1000.0
                
                # ISRC
                if 'isrcs' in recording and recording['isrcs']:
                    metadata['isrc'] = recording['isrcs'][0]
                
                # MusicBrainz ID
                metadata['musicbrainz_id'] = recording.get('id', '')
                
                # Artistes du morceau
                if 'artist-credit' in recording:
                    artists = []
                    for credit in recording['artist-credit']:
                        if isinstance(credit, dict) and 'artist' in credit:
                            artist_name = credit['artist'].get('name', '')
                            if artist_name:
                                artists.append(artist_name)
                                # Premier artiste comme ID MusicBrainz
                                if not metadata.get('musicbrainz_artist_id'):
                                    metadata['musicbrainz_artist_id'] = credit['artist'].get('id', '')
                    
                    metadata['artist'] = ', '.join(artists) if artists else ''
                
                # Informations de release
                if 'releases' in recording:
                    release = recording['releases'][0] if recording['releases'] else {}
                    
                    # Album
                    metadata['album'] = release.get('title', '')
                    metadata['musicbrainz_album_id'] = release.get('id', '')
                    
                    # Année
                    if 'date' in release:
                        try:
                            year = release['date'][:4]  # Premier 4 caractères
                            metadata['year'] = int(year) if year.isdigit() else None
                        except:
                            pass
                    
                    # Pays
                    if 'country' in release:
                        metadata['country'] = release['country']
                    
                    # Label
                    if 'label-info' in release:
                        labels = []
                        for label_info in release['label-info']:
                            if 'label' in label_info:
                                label_name = label_info['label'].get('name', '')
                                if label_name:
                                    labels.append(label_name)
                                
                                # Numéro de catalogue
                                if 'catalog-number' in label_info:
                                    metadata['catalog_number'] = label_info['catalog-number']
                        
                        metadata['label'] = ', '.join(labels) if labels else ''
                    
                    # Artiste d'album (différent de l'artiste du morceau)
                    if 'artist-credit' in release:
                        album_artists = []
                        for credit in release['artist-credit']:
                            if isinstance(credit, dict) and 'artist' in credit:
                                artist_name = credit['artist'].get('name', '')
                                if artist_name:
                                    album_artists.append(artist_name)
                        
                        metadata['album_artist'] = ', '.join(album_artists) if album_artists else metadata.get('artist', '')
                    
                    # Numéro de piste
                    if 'media' in release:
                        for medium in release['media']:
                            if 'tracks' in medium:
                                for i, track in enumerate(medium['tracks']):
                                    if track.get('recording', {}).get('id') == recording.get('id'):
                                        metadata['track_number'] = track.get('position', i + 1)
                                        metadata['total_tracks'] = len(medium['tracks'])
                                        break
        
        except Exception as e:
            self.logger.error(f"Erreur extraction MusicBrainz: {e}")
        
        return metadata
    
    def extract_from_acousticid(self, acousticid_data: Dict) -> Dict[str, Any]:
        """Extrait les métadonnées depuis une réponse AcousticID"""
        metadata = {}
        
        try:
            if 'results' in acousticid_data:
                for result in acousticid_data['results']:
                    if 'recordings' in result:
                        for recording in result['recordings']:
                            # Utiliser la première recording avec des données complètes
                            if 'title' in recording:
                                # Réutiliser l'extracteur MusicBrainz
                                mb_data = {'recordings': [recording]}
                                extracted = self.extract_from_musicbrainz(mb_data)
                                metadata.update(extracted)
                                break
                    
                    if metadata:  # Si on a trouvé des données, arrêter
                        break
        
        except Exception as e:
            self.logger.error(f"Erreur extraction AcousticID: {e}")
        
        return metadata
    
    def extract_from_lastfm(self, lastfm_data: Dict) -> Dict[str, Any]:
        """Extrait les métadonnées depuis une réponse Last.fm"""
        metadata = {}
        
        try:
            if 'track' in lastfm_data:
                track = lastfm_data['track']
                
                # Informations de base
                metadata['title'] = track.get('name', '')
                
                # Durée (en secondes depuis Last.fm)
                if 'duration' in track:
                    try:
                        metadata['duration'] = float(track['duration']) / 1000.0  # ms vers s
                    except:
                        pass
                
                # Artiste
                if 'artist' in track:
                    if isinstance(track['artist'], dict):
                        metadata['artist'] = track['artist'].get('name', '')
                        metadata['musicbrainz_artist_id'] = track['artist'].get('mbid', '')
                    else:
                        metadata['artist'] = str(track['artist'])
                
                # Album
                if 'album' in track:
                    if isinstance(track['album'], dict):
                        metadata['album'] = track['album'].get('title', '')
                        metadata['musicbrainz_album_id'] = track['album'].get('mbid', '')
                        
                        # Artiste d'album
                        if 'artist' in track['album']:
                            metadata['album_artist'] = track['album']['artist']
                    else:
                        metadata['album'] = str(track['album'])
                
                # Tags comme genres
                if 'toptags' in track and 'tag' in track['toptags']:
                    tags = []
                    for tag in track['toptags']['tag']:
                        tag_name = tag.get('name', '') if isinstance(tag, dict) else str(tag)
                        if tag_name:
                            tags.append(tag_name)
                    
                    if tags:
                        metadata['genre'] = ', '.join(tags[:3])  # Top 3 tags
                        metadata['style'] = ', '.join(tags[3:6]) if len(tags) > 3 else ''
                
                # MusicBrainz ID
                metadata['musicbrainz_id'] = track.get('mbid', '')
        
        except Exception as e:
            self.logger.error(f"Erreur extraction Last.fm: {e}")
        
        return metadata
    
    def extract_from_discogs(self, discogs_data: Dict) -> Dict[str, Any]:
        """Extrait les métadonnées depuis une réponse Discogs"""
        metadata = {}
        
        try:
            if 'results' in discogs_data:
                for result in discogs_data['results']:
                    # Titre et artiste
                    metadata['title'] = result.get('title', '')
                    
                    # Année
                    if 'year' in result:
                        try:
                            metadata['year'] = int(result['year'])
                        except:
                            pass
                    
                    # Genres et styles
                    if 'genre' in result:
                        metadata['genre'] = ', '.join(result['genre']) if isinstance(result['genre'], list) else result['genre']
                    
                    if 'style' in result:
                        metadata['style'] = ', '.join(result['style']) if isinstance(result['style'], list) else result['style']
                    
                    # Label
                    if 'label' in result:
                        metadata['label'] = ', '.join(result['label']) if isinstance(result['label'], list) else result['label']
                    
                    # Numéro de catalogue
                    if 'catno' in result:
                        metadata['catalog_number'] = result['catno']
                    
                    # Format
                    if 'format' in result:
                        metadata['format'] = ', '.join(result['format']) if isinstance(result['format'], list) else result['format']
                    
                    break  # Utiliser le premier résultat
        
        except Exception as e:
            self.logger.error(f"Erreur extraction Discogs: {e}")
        
        return metadata
    
    def merge_metadata(self, *metadata_sources: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne les métadonnées de plusieurs sources en privilégiant la qualité"""
        merged = {}
        
        # Ordre de priorité des sources (dernière = priorité la plus haute)
        priority_order = ['discogs', 'lastfm', 'acousticid', 'musicbrainz']
        
        for source_metadata in metadata_sources:
            for key, value in source_metadata.items():
                if value and value != '':  # Ignorer les valeurs vides
                    # Cas spéciaux pour certains champs
                    if key in ['genre', 'style'] and key in merged:
                        # Combiner les genres/styles sans doublons
                        existing = set(merged[key].split(', ')) if merged[key] else set()
                        new_tags = set(str(value).split(', '))
                        combined = existing.union(new_tags)
                        merged[key] = ', '.join(sorted(combined))
                    else:
                        merged[key] = value
        
        # Nettoyage final
        self._clean_metadata(merged)
        
        return merged
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> None:
        """Nettoie et normalise les métadonnées"""
        # Nettoyer les chaînes
        for key in ['title', 'artist', 'album_artist', 'album', 'genre', 'style', 'label']:
            if key in metadata and isinstance(metadata[key], str):
                # Supprimer les espaces multiples et trim
                metadata[key] = ' '.join(metadata[key].split()).strip()
        
        # Normaliser les nombres
        for key in ['year', 'track_number', 'total_tracks', 'disc_number', 'total_discs']:
            if key in metadata:
                try:
                    metadata[key] = int(metadata[key])
                except:
                    del metadata[key]
        
        # S'assurer que album_artist existe
        if 'album_artist' not in metadata and 'artist' in metadata:
            metadata['album_artist'] = metadata['artist']
    
    def validate_metadata_completeness(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Valide la complétude des métadonnées et retourne un rapport"""
        required_fields = ['title', 'artist', 'album']
        recommended_fields = ['album_artist', 'year', 'genre', 'track_number']
        optional_fields = ['style', 'label', 'catalog_number', 'isrc', 'duration']
        
        report = {
            'completeness_score': 0,
            'missing_required': [],
            'missing_recommended': [],
            'present_fields': [],
            'total_fields': len(metadata)
        }
        
        # Vérifier les champs requis
        for field in required_fields:
            if field in metadata and metadata[field]:
                report['present_fields'].append(field)
                report['completeness_score'] += 30  # 30 points par champ requis
            else:
                report['missing_required'].append(field)
        
        # Vérifier les champs recommandés
        for field in recommended_fields:
            if field in metadata and metadata[field]:
                report['present_fields'].append(field)
                report['completeness_score'] += 15  # 15 points par champ recommandé
            else:
                report['missing_recommended'].append(field)
        
        # Vérifier les champs optionnels
        for field in optional_fields:
            if field in metadata and metadata[field]:
                report['present_fields'].append(field)
                report['completeness_score'] += 5  # 5 points par champ optionnel
        
        # Score sur 100
        max_score = len(required_fields) * 30 + len(recommended_fields) * 15 + len(optional_fields) * 5
        report['completeness_percentage'] = min(100, (report['completeness_score'] / max_score) * 100)
        
        return report

def test_metadata_extractor():
    """Test de l'extracteur de métadonnées"""
    extractor = AdvancedMetadataExtractor()
    
    # Test avec des données factices MusicBrainz
    mb_data = {
        'recordings': [{
            'title': 'Test Song',
            'length': 240000,  # 4 minutes
            'id': 'test-mb-id',
            'artist-credit': [{'artist': {'name': 'Test Artist', 'id': 'artist-id'}}],
            'releases': [{
                'title': 'Test Album',
                'id': 'album-id',
                'date': '2023-01-15',
                'country': 'US',
                'artist-credit': [{'artist': {'name': 'Album Artist'}}],
                'label-info': [{'label': {'name': 'Test Label'}, 'catalog-number': 'TL001'}]
            }]
        }]
    }
    
    metadata = extractor.extract_from_musicbrainz(mb_data)
    report = extractor.validate_metadata_completeness(metadata)
    
    print("🧪 Test de l'extracteur de métadonnées")
    print("=" * 50)
    print(f"📊 Métadonnées extraites: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
    print(f"\n📋 Rapport de complétude:")
    print(f"   Score: {report['completeness_percentage']:.1f}%")
    print(f"   Champs présents: {', '.join(report['present_fields'])}")
    if report['missing_recommended']:
        print(f"   Manquants recommandés: {', '.join(report['missing_recommended'])}")

if __name__ == "__main__":
    test_metadata_extractor()
