# Interface Graphique MusicFolderManager 🎵

Interface graphique complète pour tester et utiliser toutes les fonctionnalités de MusicFolderManager.

## 🚀 Démarrage

### Méthode 1: Lanceur direct
```bash
python interface_ui/launcher.py
```

### Méthode 2: Module principal
```bash
python interface_ui/main_gui.py
```

### Méthode 3: Depuis la racine du projet
```bash
python -m interface_ui.launcher
```

## 📋 Fonctionnalités

### 🔧 Onglet Configuration
- **Sélection de répertoire**: Choisir le dossier musical à analyser
- **Configuration API**: Entrer votre clé AcoustID
- **Répertoire de sortie**: Choisir où organiser les fichiers
- **Options avancées**:
  - Mode simulation (Dry Run)
  - Activation de l'organisation
  - Création de dossiers par année
  - Déplacement vs copie des fichiers

### 🔍 Onglet Analyse
- **Informations sur le répertoire**: Statistiques des fichiers trouvés
- **Barre de progression**: Suivi en temps réel
- **Analyse automatique**: Détection et traitement des fichiers audio

### 📁 Onglet Organisation
- **Pattern de nommage**: Configuration du format de sortie
- **Variables disponibles**: `{artist}`, `{album}`, `{title}`, `{year}`, `{track}`, `{genre}`
- **Aperçu en temps réel**: Voir comment les fichiers seront organisés
- **Exemples visuels**: Prévisualisation avec des données de test

### 🧪 Onglet Tests
- **Tests unitaires individuels**:
  - Test MetadataManager
  - Test FileOrganizer  
  - Test AudioFingerprinter
- **Console de logs colorée**: Suivi détaillé de tous les processus
- **Test complet**: Lance tous les tests d'un coup

## 🎯 Utilisation Recommandée

### Première utilisation
1. **Configuration**: Remplir tous les champs dans l'onglet Configuration
2. **Test**: Utiliser l'onglet Tests pour vérifier que tout fonctionne
3. **Simulation**: Activer "Mode simulation" et tester l'organisation
4. **Production**: Désactiver la simulation et lancer l'organisation réelle

### Workflow typique
```
📂 Sélectionner répertoire
🔑 Entrer clé API AcoustID
🔧 Configurer options
🧪 Lancer tests (optionnel)
🔍 Analyser les fichiers
📁 Générer aperçu organisation
✅ Organiser (avec simulation d'abord)
```

## ⚠️ Mode Simulation

Le **mode simulation (Dry Run)** est **fortement recommandé** pour:
- Tester la configuration
- Vérifier les patterns de nommage
- Prévisualiser l'organisation
- Éviter les erreurs sur vos fichiers

## 🎨 Interface

### Couleurs des logs
- 🔵 **Bleu**: Informations générales
- 🟢 **Vert**: Succès/réussites
- 🔴 **Rouge**: Erreurs
- 🟠 **Orange**: Avertissements

### Raccourcis clavier
- `Ctrl+L`: Effacer les logs (focus sur console)
- `F5`: Actualiser l'aperçu
- `Esc`: Fermer les dialogues

## 🔧 Configuration Avancée

### Patterns de nommage exemples
```
{artist}/{album}/{track:02d} - {title}
→ Queen/Greatest Hits/01 - Bohemian Rhapsody.mp3

{year}/{artist} - {album}/{title}
→ 1975/Queen - A Night at the Opera/Bohemian Rhapsody.mp3

{genre}/{artist}/{year} - {album}/{track:02d}. {title}
→ Rock/Queen/1975 - A Night at the Opera/01. Bohemian Rhapsody.mp3
```

### Variables disponibles
- `{artist}`: Nom de l'artiste
- `{album}`: Nom de l'album
- `{title}`: Titre de la chanson
- `{year}`: Année de sortie
- `{track}`: Numéro de piste
- `{track:02d}`: Numéro de piste avec zéros (01, 02, etc.)
- `{genre}`: Genre musical

## 🚨 Dépannage

### Interface ne se lance pas
```bash
# Vérifier que tkinter est installé
python -c "import tkinter; print('tkinter OK')"

# Vérifier les imports
python -c "from organizer.metadata_manager import MetadataManager; print('Imports OK')"
```

### Erreurs de modules
Assurez-vous d'être dans le répertoire racine du projet:
```bash
cd /path/to/MusicFolderManager
python interface_ui/launcher.py
```

### Problèmes d'API
- Vérifiez votre clé AcoustID
- Testez avec le mode simulation d'abord
- Consultez les logs pour les détails des erreurs

## 📊 Exemples de Tests

L'interface inclut des données de test pour:
- **Queen**: Bohemian Rhapsody, A Night at the Opera (1975)
- **The Beatles**: Come Together, Abbey Road (1969)
- **Pink Floyd**: Another Brick in the Wall, The Wall (1979)
- **Led Zeppelin**: Stairway to Heaven, IV (1971)

Ces exemples permettent de tester toutes les fonctionnalités sans avoir besoin de vrais fichiers audio.

## 🎵 Bon Usage !

L'interface graphique rend MusicFolderManager accessible à tous, que vous soyez développeur ou utilisateur final. Profitez de toutes les fonctionnalités avancées dans un environnement convivial !
