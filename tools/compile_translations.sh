#!/bin/sh
# Компілює po/*.po у src/inkfist/locale/<мова>/LC_MESSAGES/inkfist.mo
# Потрібен пакет gettext:  sudo apt install gettext
set -e
cd "$(dirname "$0")/.."
for po in po/*.po; do
    lang=$(basename "$po" .po)
    mkdir -p "src/inkfist/locale/$lang/LC_MESSAGES"
    msgfmt --check -o "src/inkfist/locale/$lang/LC_MESSAGES/inkfist.mo" "$po"
    echo "  $lang: OK"
done
