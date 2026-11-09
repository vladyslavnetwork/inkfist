#!/bin/sh
# Оновлює шаблон po/inkfist.pot з коду та підтягує нові рядки в усі po/*.po
set -e
cd "$(dirname "$0")/.."
xgettext --language=Python --keyword=_ --from-code=UTF-8 \
    --package-name=inkfist -o po/inkfist.pot src/inkfist/*.py
for po in po/*.po; do
    msgmerge --update --backup=none "$po" po/inkfist.pot
done
