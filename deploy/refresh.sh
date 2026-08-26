#!/usr/bin/env bash
#
# refresh.sh — régénère l'instantané et le publie dans le web root.
# Lancé par le timer systemd (ou manuellement). Aucune entrée réseau ouverte :
# le script contacte BCE/Eurostat en sortie HTTPS uniquement.
#
set -euo pipefail

APP_DIR="/opt/euromacro"                 # code + venv (jamais servi par Apache)
WEB_DIR="/var/www/html/euromacro"         # web root statique (servi par Apache)
BACKUP_DIR="$APP_DIR/.last-good"
REVISION_FILE="$APP_DIR/DEPLOYED_SHA"
ATTESTED_REVISION_FILE="${EUROMACRO_ATTESTED_SHA_FILE:-$APP_DIR/L0G_ATTESTED_SHA}"

cd "$APP_DIR"

if [[ ! -f "$REVISION_FILE" ]] || ! grep -Eq '^[0-9a-f]{40}$' "$REVISION_FILE"; then
    echo "REFUS — DEPLOYED_SHA absent ou invalide" >&2
    exit 1
fi
if [[ ! -f "$ATTESTED_REVISION_FILE" ]] || ! grep -Eq '^[0-9a-f]{40}$' "$ATTESTED_REVISION_FILE"; then
    echo "REFUS — attestation l0g absente ou invalide" >&2
    exit 1
fi
export EUROMACRO_SOURCE_SHA
EUROMACRO_SOURCE_SHA="$(tr -d '[:space:]' < "$REVISION_FILE")"
L0G_ATTESTED_SHA="$(tr -d '[:space:]' < "$ATTESTED_REVISION_FILE")"
if [[ "$EUROMACRO_SOURCE_SHA" != "$L0G_ATTESTED_SHA" ]]; then
    echo "REFUS — révision Euro non attestée par l’agrégateur l0g" >&2
    exit 1
fi

# Génère et valide dans APP_DIR. Rien n'est publié si la couverture, les dates
# sources, les indicateurs critiques ou la traçabilité sont invalides.
"$APP_DIR/.venv/bin/python" "$APP_DIR/build_snapshot.py"
"$APP_DIR/.venv/bin/python" "$APP_DIR/validate_snapshot.py" "$APP_DIR/snapshot.json"

mkdir -p "$BACKUP_DIR"
for name in index.html snapshot.js snapshot.json; do
    if [[ -f "$WEB_DIR/$name" ]]; then
        install -m 0644 "$WEB_DIR/$name" "$BACKUP_DIR/$name"
    fi
done

rollback() {
    echo "Échec de publication — restauration du dernier lot valide" >&2
    for name in index.html snapshot.js snapshot.json; do
        if [[ -f "$BACKUP_DIR/$name" ]]; then
            install -m 0644 "$BACKUP_DIR/$name" "$WEB_DIR/$name"
        fi
    done
}
trap rollback ERR

# Les trois fichiers sont d'abord préparés sous des noms refusés par Apache,
# puis promus. Le trap restaure le lot précédent si une promotion échoue.
install -m 0644 "$APP_DIR/index.html"     "$WEB_DIR/.index.html.new"
install -m 0644 "$APP_DIR/snapshot.js"   "$WEB_DIR/.snapshot.js.new"
install -m 0644 "$APP_DIR/snapshot.json" "$WEB_DIR/.snapshot.json.new"
mv "$WEB_DIR/.index.html.new"     "$WEB_DIR/index.html"
mv "$WEB_DIR/.snapshot.js.new"   "$WEB_DIR/snapshot.js"
mv "$WEB_DIR/.snapshot.json.new" "$WEB_DIR/snapshot.json"
trap - ERR

echo "Publié dans $WEB_DIR à $(date -Is) — SHA $EUROMACRO_SOURCE_SHA"
