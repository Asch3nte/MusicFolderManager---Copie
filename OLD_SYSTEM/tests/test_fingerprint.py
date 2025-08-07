#!/usr/bin/env python3
"""
Tests unitaires pour le module AudioFingerprinter
"""

import unittest
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from fingerprint.processor import AudioFingerprinter

class TestAudioFingerprinter(unittest.TestCase):
    
    def setUp(self):
        """Configuration des tests"""
        self.api_key = "TEST_KEY"
        self.fp = AudioFingerprinter(self.api_key)
    
    def test_fingerprinter_initialization(self):
        """Test d'initialisation de AudioFingerprinter"""
        self.assertEqual(self.fp.api_key, "TEST_KEY")
        self.assertIsNotNone(self.fp.cache)
        self.assertIsNotNone(self.fp.config)
        self.assertIsNotNone(self.fp.logger)
        self.assertEqual(self.fp.max_retries, 3)
    
    def test_fingerprint_generation_with_mock_file(self):
        """Test de génération d'empreinte avec un fichier mock"""
        # Note: Ce test nécessiterait un vrai fichier audio pour fonctionner
        # En pratique, vous devriez utiliser un fichier audio de test
        
        # Exemple de ce à quoi le test devrait ressembler avec un vrai fichier:
        # duration, fingerprint = self.fp.get_fingerprint("test_audio.mp3")
        # self.assertIsInstance(duration, float)
        # self.assertIsInstance(fingerprint, str)
        # self.assertGreater(len(fingerprint), 100)  # Format base64 typique
        
        # Pour l'instant, testons juste que la méthode existe
        self.assertTrue(hasattr(self.fp, 'get_fingerprint'))
        self.assertTrue(callable(getattr(self.fp, 'get_fingerprint')))
    
    def test_query_acoustid_method_exists(self):
        """Test que la méthode query_acoustid existe et est callable"""
        self.assertTrue(hasattr(self.fp, 'query_acoustid'))
        self.assertTrue(callable(getattr(self.fp, 'query_acoustid')))
    
    def test_resolve_metadata_method_exists(self):
        """Test que la méthode resolve_metadata existe"""
        self.assertTrue(hasattr(self.fp, 'resolve_metadata'))
        self.assertTrue(callable(getattr(self.fp, 'resolve_metadata')))
    
    def test_format_updates_method(self):
        """Test de la méthode _format_updates"""
        mock_metadata = {
            'title': 'Test Song',
            'artists': [{'name': 'Test Artist'}],
            'release': {'title': 'Test Album'}
        }
        
        result = self.fp._format_updates(mock_metadata)
        
        self.assertEqual(result['title'], 'Test Song')
        self.assertEqual(result['artist'], 'Test Artist')
        self.assertEqual(result['album'], 'Test Album')
    
    def test_format_updates_with_missing_data(self):
        """Test de _format_updates avec des données manquantes"""
        mock_metadata = {}
        
        result = self.fp._format_updates(mock_metadata)
        
        self.assertEqual(result['title'], '')
        self.assertEqual(result['artist'], '')
        self.assertEqual(result['album'], '')

# Test avec un fichier audio réel (à décommenter si vous avez un fichier de test)
class TestWithRealAudioFile(unittest.TestCase):
    """
    Tests nécessitant un vrai fichier audio.
    Décommentez et adaptez si vous avez un fichier de test disponible.
    """
    
    def setUp(self):
        self.api_key = "TEST_KEY"
        self.fp = AudioFingerprinter(self.api_key)
        # self.test_audio_file = "path/to/test_audio.mp3"  # Remplacer par un vrai chemin
    
    # def test_fingerprint_generation(self):
    #     """Test unitaire pour get_fingerprint avec un vrai fichier"""
    #     if os.path.exists(self.test_audio_file):
    #         duration, fingerprint = self.fp.get_fingerprint(self.test_audio_file)
    #         self.assertIsInstance(duration, float)
    #         self.assertIsInstance(fingerprint, str)
    #         self.assertGreater(len(fingerprint), 100)  # Format base64 typique
    #         self.assertGreater(duration, 0)  # Durée positive
    #     else:
    #         self.skipTest(f"Fichier de test {self.test_audio_file} non trouvé")

if __name__ == '__main__':
    # Lancer les tests
    unittest.main(verbosity=2)
