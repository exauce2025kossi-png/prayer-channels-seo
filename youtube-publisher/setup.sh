#!/usr/bin/env bash
# setup.sh — Installation complète du système de publication YouTube
set -e

echo "======================================================"
echo " 🎬 YouTube Auto Publisher — KODJOVI SOKE KOSSI"
echo "======================================================"

# 1. Python check
if ! command -v python3 &>/dev/null; then
  echo "❌ Python3 non trouvé. Installez Python 3.8+ depuis https://python.org"
  exit 1
fi
echo "✅ Python : $(python3 --version)"

# 2. Pip install
echo ""
echo "📦 Installation des dépendances..."
pip3 install -r requirements.txt --quiet
echo "✅ Dépendances installées."

# 3. Dossier vidéos
mkdir -p videos
echo "✅ Dossier videos/ créé."

# 3b. Génération automatique des vidéos
echo ""
echo "======================================================"
echo " 🎬 GÉNÉRATION DES VIDÉOS (30 chansons pour enfants)"
echo "======================================================"
echo " → Cela peut prendre 5-10 minutes..."
echo " → Les vidéos seront créées dans le dossier videos/"
echo "======================================================"
echo ""

# Installer espeak-ng si absent (Linux)
if ! command -v espeak-ng &>/dev/null; then
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y espeak-ng --quiet
  fi
fi

python3 video_generator.py
echo "✅ Vidéos générées !"

# 4. Authentification (ouvrira le navigateur)
echo ""
echo "======================================================"
echo " 🔐 AUTHENTIFICATION YOUTUBE"
echo "======================================================"
echo " → Un navigateur va s'ouvrir."
echo " → Connectez-vous avec le compte Google de votre chaîne."
echo " → Acceptez les permissions demandées."
echo " → Revenez ici une fois terminé."
echo "======================================================"
echo ""
python3 -c "from auth import get_youtube; yt = get_youtube(); print('✅ Connecté à YouTube !')"

# 5. Optimisation de la chaîne
echo ""
echo "🔧 Optimisation de la chaîne en cours..."
python3 optimizer.py
echo "✅ Chaîne optimisée !"

# 6. Cron job (Linux/Mac)
echo ""
echo "======================================================"
echo " ⏰ CONFIGURATION PUBLICATION AUTOMATIQUE"
echo "======================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_CMD="0 10 * * * cd $SCRIPT_DIR && python3 publisher.py >> $SCRIPT_DIR/publish.log 2>&1"

echo "Ajout du cron job (publication à 10h00 chaque jour)..."
(crontab -l 2>/dev/null | grep -v "publisher.py"; echo "$CRON_CMD") | crontab -
echo "✅ Cron job configuré !"

echo ""
echo "======================================================"
echo " ✅ INSTALLATION TERMINÉE !"
echo "======================================================"
echo ""
echo " 📋 Prochaines étapes :"
echo "   1. Les vidéos ont été générées automatiquement dans videos/"
echo "      (30 chansons pour enfants : ABC Song, Baby Shark, Dinosaur Song...)"
echo ""
echo "   2. Voir le planning :"
echo "      python3 publisher.py --list"
echo ""
echo "   3. Tester avec une publication manuelle :"
echo "      python3 publisher.py --date 2026-05-02"
echo ""
echo "   4. Mode automatique (publie à 10h chaque jour) :"
echo "      Le cron job est déjà activé !"
echo ""
echo " 🔗 Votre chaîne : https://www.youtube.com/channel/UCeKrNU3hvLfm5sHfHyXFSeg"
echo "======================================================"
