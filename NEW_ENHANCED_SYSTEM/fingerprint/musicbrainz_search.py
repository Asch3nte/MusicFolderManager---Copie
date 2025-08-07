#!/usr/bin/env python3
"""
Module de recherche textuelle MusicBrainz
Fallback intelligent quand AcoustID échoue
"""

import musicbrainzngs
import re
import os
from pathlib import Path

class MusicBrainzSearcher:
    def __init__(self, logger=None):
        self.logger = logger
        
        # Configuration de l'API MusicBrainz
        musicbrainzngs.set_useragent(
            "MusicFolderManager", 
            "1.0", 
            "https://github.com/user/musicfoldermanager"
        )
        
        # Limite de résultats pour éviter la surcharge
        self.max_results = 5
    
    def search_by_filename(self, file_path):
        """Recherche basée sur le nom de fichier"""
        try:
            filename = os.path.basename(file_path)
            extracted = self._extract_info_from_filename(filename)
            
            if not extracted['artist'] and not extracted['title']:
                return None
            
            self.logger.info(f"🔍 Recherche MusicBrainz: {extracted['artist']} - {extracted['title']}")
            
            # Recherche avec les informations extraites
            return self._search_musicbrainz(
                artist=extracted['artist'],
                title=extracted['title'],
                album=extracted.get('album')
            )
            
        except Exception as e:
            self.logger.warning(f"Erreur recherche MusicBrainz: {e}")
            return None
    
    def search_by_metadata(self, metadata):
        """Recherche enrichie basée sur des métadonnées existantes"""
        try:
            artist = metadata.get('artist', '')
            title = metadata.get('title', '')
            album = metadata.get('album', '')
            albumartist = metadata.get('albumartist', '')
            catalognumber = metadata.get('catalognumber', '')
            musicbrainz_trackid = metadata.get('musicbrainz_trackid', '')
            
            # Si on a un MusicBrainz ID, recherche directe
            if musicbrainz_trackid:
                self.logger.info(f"🆔 Recherche directe MusicBrainz ID: {musicbrainz_trackid}")
                try:
                    result = musicbrainzngs.get_recording_by_id(
                        musicbrainz_trackid,
                        includes=['artists', 'releases', 'artist-credits']
                    )
                    if result and 'recording' in result:
                        # Transformer en format de recherche
                        return {
                            'best_match': {
                                'recording': result['recording'],
                                'confidence': 1.0  # Confiance maximale pour un ID exact
                            }
                        }
                except:
                    self.logger.info("ID MusicBrainz invalide ou introuvable, recherche par métadonnées")
            
            if not artist and not title:
                return None
            
            # Stratégie de recherche progressive
            search_strategies = [
                # 1. Recherche avec catalog number (très précise) - on l'intègre dans une requête spéciale
                {
                    'params': {'artist': artist, 'title': title, 'album': album} if not catalognumber else None,
                    'desc': f"avec numéro de catalogue: {catalognumber}",
                    'condition': bool(catalognumber),
                    'special': 'catno'  # Marqueur spécial
                },
                # 2. Recherche avec album artist + album + titre (très précise)
                {
                    'params': {'artist': albumartist, 'title': title, 'album': album},
                    'desc': f"albumartist + album: {albumartist} - {title} [{album}]",
                    'condition': bool(albumartist and album)
                },
                # 3. Recherche avec track artist + album + titre (précise)
                {
                    'params': {'artist': artist, 'title': title, 'album': album},
                    'desc': f"artist + album: {artist} - {title} [{album}]",
                    'condition': bool(album)
                },
                # 4. Recherche track artist + titre seulement (moins précise)
                {
                    'params': {'artist': artist, 'title': title},
                    'desc': f"artist + titre: {artist} - {title}",
                    'condition': True
                }
            ]
            
            # Essayer chaque stratégie
            for strategy in search_strategies:
                if not strategy['condition']:
                    continue
                    
                self.logger.info(f"🔍 Stratégie MusicBrainz: {strategy['desc']}")
                
                # Cas spécial : recherche par numéro de catalogue
                if strategy.get('special') == 'catno':
                    result = self._search_by_catalog_number(catalognumber, artist, title)
                else:
                    result = self._search_musicbrainz(**strategy['params'])
                
                if result and result.get('best_match', {}).get('confidence', 0) > 0.7:
                    self.logger.info(f"✅ Correspondance trouvée avec confiance {result['best_match']['confidence']:.1%}")
                    return result
                elif result:
                    self.logger.info(f"⚠️ Correspondance faible: {result['best_match']['confidence']:.1%}")
            
            # Si aucune stratégie n'a donné de bon résultat, retourner le meilleur
            return self._search_musicbrainz(artist=artist, title=title, album=album)
            
        except Exception as e:
            self.logger.warning(f"Erreur recherche MusicBrainz métadonnées: {e}")
            return None

    def _search_by_catalog_number(self, catno, artist='', title=''):
        """Recherche spécialisée par numéro de catalogue"""
        try:
            # Recherche par catno dans les releases
            releases = musicbrainzngs.search_releases(catno=catno, limit=5)
            
            if not releases.get('release-list'):
                return None
            
            # Pour chaque release trouvé, chercher les recordings qui matchent
            best_match = None
            best_confidence = 0
            
            for release in releases['release-list']:
                try:
                    # Obtenir les détails du release avec les recordings
                    release_detail = musicbrainzngs.get_release_by_id(
                        release['id'], 
                        includes=['recordings', 'artist-credits']
                    )
                    
                    if 'medium-list' in release_detail['release']:
                        for medium in release_detail['release']['medium-list']:
                            if 'track-list' in medium:
                                for track in medium['track-list']:
                                    recording = track.get('recording', {})
                                    
                                    # Calculer la correspondance avec artist/title
                                    confidence = self._calculate_match_confidence(
                                        recording, artist, title
                                    )
                                    
                                    if confidence > best_confidence:
                                        best_confidence = confidence
                                        best_match = {
                                            'recording': recording,
                                            'confidence': confidence
                                        }
                                        
                except Exception as e:
                    continue
            
            if best_match and best_confidence > 0.3:  # Seuil minimal
                return {'best_match': best_match}
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur recherche par catalogue: {e}")
            return None

    def _calculate_match_confidence(self, recording, target_artist, target_title):
        """Calcule la confiance de correspondance entre un recording et les critères"""
        try:
            confidence = 0.0
            
            # Comparaison du titre
            recording_title = recording.get('title', '').lower() if recording.get('title') else ''
            if target_title and recording_title:
                title_similarity = self._string_similarity(recording_title, target_title.lower())
                confidence += title_similarity * 0.6  # 60% du poids
            
            # Comparaison de l'artiste
            recording_artist = ''
            if 'artist-credit' in recording:
                artists = []
                for credit in recording['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                recording_artist = ', '.join(artists).lower()
            
            if target_artist and recording_artist:
                artist_similarity = self._string_similarity(recording_artist, target_artist.lower())
                confidence += artist_similarity * 0.4  # 40% du poids
            
            return min(confidence, 1.0)  # Plafonner à 1.0
            
        except Exception:
            return 0.0

    def _string_similarity(self, s1, s2):
        """Calcule la similarité entre deux chaînes (simple)"""
        if not s1 or not s2:
            return 0.0
        
        # Normaliser
        s1 = re.sub(r'[^\w\s]', '', s1.lower()).strip()
        s2 = re.sub(r'[^\w\s]', '', s2.lower()).strip()
        
        if s1 == s2:
            return 1.0
        
        # Similarité basique basée sur les mots communs
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_info_from_filename(self, filename):
        """Extrait artiste, titre, album du nom de fichier"""
        # Supprimer l'extension
        name = os.path.splitext(filename)[0]
        
        # Nettoyer les patterns courants
        name = re.sub(r'\(.*?\)', '', name)  # Supprimer (Original Mix), etc.
        name = re.sub(r'\[.*?\]', '', name)  # Supprimer [Label], etc.
        
        # Patterns d'extraction (ordre d'importance)
        patterns = [
            # "02. Artiste - Titre"
            r'^\d+\.?\s*(.+?)\s*-\s*(.+)$',
            # "Artiste - Titre"
            r'^(.+?)\s*-\s*(.+)$',
            # "Artiste_Titre"
            r'^(.+?)_(.+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name.strip())
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    artist = groups[0].strip()
                    title = groups[1].strip()
                    
                    # Nettoyer encore
                    artist = self._clean_text(artist)
                    title = self._clean_text(title)
                    
                    if artist and title:
                        return {
                            'artist': artist,
                            'title': title,
                            'album': None
                        }
        
        # Si aucun pattern, essayer de deviner
        if ' - ' in name:
            parts = name.split(' - ', 1)
            return {
                'artist': self._clean_text(parts[0]),
                'title': self._clean_text(parts[1]),
                'album': None
            }
        
        return {'artist': '', 'title': name.strip(), 'album': None}
    
    def _clean_text(self, text):
        """Nettoie le texte pour la recherche"""
        if not text:
            return ''
        
        # Supprimer les caractères spéciaux problématiques
        text = re.sub(r'[_\[\](){}]', ' ', text)
        text = re.sub(r'\s+', ' ', text)  # Multiples espaces → un seul
        return text.strip()
    
    def _search_musicbrainz(self, artist='', title='', album=None):
        """Effectue la recherche sur MusicBrainz"""
        try:
            # Construction de la requête
            query_parts = []
            
            if artist:
                query_parts.append(f'artist:"{artist}"')
            if title:
                query_parts.append(f'recording:"{title}"')
            if album:
                query_parts.append(f'release:"{album}"')
            
            if not query_parts:
                return None
            
            query = ' AND '.join(query_parts)
            self.logger.debug(f"Requête MusicBrainz: {query}")
            
            # Recherche
            result = musicbrainzngs.search_recordings(
                query=query,
                limit=self.max_results,
                strict=False
            )
            
            recordings = result.get('recording-list', [])
            
            if not recordings:
                # Recherche plus permissive sans guillemets
                query_parts = []
                if artist:
                    query_parts.append(f'artist:{artist}')
                if title:
                    query_parts.append(f'recording:{title}')
                
                query = ' AND '.join(query_parts)
                self.logger.debug(f"Requête MusicBrainz permissive: {query}")
                
                result = musicbrainzngs.search_recordings(
                    query=query,
                    limit=self.max_results,
                    strict=False
                )
                recordings = result.get('recording-list', [])
            
            if recordings:
                # Retourner TOUS les résultats avec leurs confidences
                all_matches = []
                for recording in recordings:
                    confidence = self._calculate_confidence(recording, artist, title)
                    all_matches.append({
                        'recording': recording,
                        'confidence': confidence,
                        'source': 'musicbrainz_text_search'
                    })
                
                # Trier par confiance décroissante
                all_matches.sort(key=lambda x: x['confidence'], reverse=True)
                
                self.logger.info(f"✅ MusicBrainz trouvé: {len(all_matches)} suggestions")
                
                return {
                    'suggestions': all_matches,  # Toutes les suggestions
                    'best_match': all_matches[0] if all_matches else None,  # Meilleure pour compatibilité
                    'total_count': len(all_matches),
                    'source': 'musicbrainz_text_search'
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur API MusicBrainz: {e}")
            return None
    
    def _calculate_confidence(self, recording, target_artist, target_title):
        """Calcule la confiance du résultat MusicBrainz"""
        try:
            # Récupérer les informations du résultat
            result_title = recording.get('title', '').lower() if recording.get('title') else ''
            result_artist = ''
            
            if 'artist-credit' in recording:
                artists = []
                for credit in recording['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                result_artist = ' '.join(artists).lower()
            
            # Comparaison simple (peut être améliorée avec des algorithmes de distance)
            title_match = self._similarity(target_title.lower(), result_title)
            artist_match = self._similarity(target_artist.lower(), result_artist)
            
            # Score combiné
            confidence = (title_match + artist_match) / 2
            
            return min(confidence, 0.95)  # Cap à 95% pour les recherches textuelles
            
        except Exception:
            return 0.5  # Confiance moyenne par défaut
    
    def _similarity(self, text1, text2):
        """Calcule la similarité entre deux textes (simple)"""
        if not text1 or not text2:
            return 0.0
        
        # Jaccard similarity basique
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def format_result(self, mb_data):
        """Formate le résultat MusicBrainz pour compatibilité"""
        try:
            # Debug: Log la structure reçue
            self.logger.debug(f"format_result reçu: {type(mb_data)} - clés: {list(mb_data.keys()) if isinstance(mb_data, dict) else 'N/A'}")
            
            # Vérifier si mb_data est None ou vide
            if not mb_data:
                self.logger.warning("format_result: mb_data est None ou vide")
                return None
            
            # Vérifier si 'recording' existe
            if 'recording' not in mb_data:
                self.logger.warning(f"format_result: clé 'recording' manquante. Clés disponibles: {list(mb_data.keys())}")
                return None
            
            recording = mb_data['recording']
            
            # Vérifier si recording est valide
            if not recording:
                self.logger.warning("format_result: recording est None ou vide")
                return None
            
            # Extraire l'artiste
            artist = 'Artiste Inconnu'
            if 'artist-credit' in recording:
                artists = []
                for credit in recording['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                if artists:
                    artist = ', '.join(artists)
            
            # Extraire l'album
            album = 'Album Inconnu'
            if 'release-list' in recording and recording['release-list']:
                album = recording['release-list'][0].get('title', 'Album Inconnu')
            
            # Extraire l'année
            year = ''
            if 'release-list' in recording and recording['release-list']:
                release = recording['release-list'][0]
                if 'date' in release:
                    year = release['date'][:4] if len(release['date']) >= 4 else ''
            
            formatted_result = {
                'artist': artist,
                'title': recording.get('title', 'Titre Inconnu'),
                'album': album,
                'year': year,
                'duration': recording.get('length', 0),
                'musicbrainz_id': recording.get('id', ''),
                'source': 'musicbrainz_text_search'
            }
            
            self.logger.debug(f"format_result formaté avec succès: {formatted_result['artist']} - {formatted_result['title']}")
            return formatted_result
            
        except Exception as e:
            self.logger.warning(f"Erreur formatage MusicBrainz: {e}")
            self.logger.warning(f"Type de mb_data: {type(mb_data)}")
            if isinstance(mb_data, dict):
                self.logger.warning(f"Clés de mb_data: {list(mb_data.keys())}")
            return None
