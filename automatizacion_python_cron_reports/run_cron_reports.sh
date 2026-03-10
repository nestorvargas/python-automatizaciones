#!/usr/bin/env bash
set -euo pipefail
# Script para ejecutar los reportes desde cron o manualmente.
# - Activa el virtualenv si existe en la raíz del proyecto o en la carpeta.
# - Ejecuta `verificar_sitios.py` y `verificar_drupal.py`, enviando salidas a logs.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Preferir venv en la raíz del repo (.venv) si existe
if [ -f "$DIR/../.venv/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$DIR/../.venv/bin/activate"
elif [ -f "$DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$DIR/.venv/bin/activate"
fi

TIMESTAMP="$(date +'%Y-%m-%d %H:%M:%S')"
echo "[$TIMESTAMP] Ejecutando verificar_sitios.py" >> "$DIR/cron.log"
python "$DIR/verificar_sitios.py" >> "$DIR/cron.log" 2>&1 || echo "[$TIMESTAMP] verificar_sitios.py falló" >> "$DIR/cron.log"

echo "[$TIMESTAMP] Ejecutando verificar_drupal.py" >> "$DIR/cron_drupal.log"
python "$DIR/verificar_drupal.py" >> "$DIR/cron_drupal.log" 2>&1 || echo "[$TIMESTAMP] verificar_drupal.py falló" >> "$DIR/cron_drupal.log"

echo "[$TIMESTAMP] Ejecución finalizada" >> "$DIR/cron.log"
