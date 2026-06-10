#!/usr/bin/env bash
#
# refresh.sh — régénère l'instantané et le publie dans le web root.
# Lancé par le timer systemd (ou manuellement). Aucune entrée réseau ouverte :
# le script contacte BCE/Eurostat en sortie HTTPS uniquement.
#
set -euo pipefail

APP_DIR="/opt/euromacro"            # code + venv (jamais servi par Apache)
WEB_DIR="/var/www/html/euromacro"        # web root statique (servi par Apache)

cd "$APP_DIR"

# Génère snapshot.js + snapshot.json dans APP_DIR
"$APP_DIR/.venv/bin/python" "$APP_DIR/build_snapshot.py"

# Publication atomique vers le web root (lecture seule pour Apache)
install -m 0644 "$APP_DIR/snapshot.js"   "$WEB_DIR/snapshot.js"
install -m 0644 "$APP_DIR/snapshot.json" "$WEB_DIR/snapshot.json"

echo "Publié dans $WEB_DIR à $(date -Is)"
