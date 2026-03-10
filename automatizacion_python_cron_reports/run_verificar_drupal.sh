#!/usr/bin/env bash
set -euo pipefail

# Wrapper para ejecutar verificar_drupal.py con rotación de logs y alertas
BASE_DIR="/Users/nestorvargas/Trabajo/desarrollo-nestor/curso-python"
LOGDIR="$BASE_DIR/automatizacion_python_cron_reports"
LOG="$LOGDIR/cron_drupal.log"
SCRIPT="$LOGDIR/verificar_drupal.py"
VENV_PY="$BASE_DIR/.venv/bin/python"

# Rotación: mantener N backups y rotar si el archivo supera SIZE
MAX_BACKUPS=7
MAX_SIZE=$((5*1024*1024)) # 5 MB

rotate_if_needed() {
  if [ -f "$LOG" ]; then
    size=$(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null || echo 0)
    if [ "$size" -gt "$MAX_SIZE" ]; then
      ts=$(date +"%Y%m%d_%H%M%S")
      mv "$LOG" "$LOG.$ts"
      gzip -9 "$LOG.$ts" || true
      # eliminar backups antiguos
      ls -1t "$LOG".* 2>/dev/null | tail -n +$((MAX_BACKUPS+1)) | xargs -r rm -f --
    fi
  fi
}

main() {
  rotate_if_needed

  # Ejecutar el script y capturar código de salida
  "$VENV_PY" "$SCRIPT" >> "$LOG" 2>&1
  rc=$?

  if [ $rc -ne 0 ]; then
    # preparar cuerpo con últimas 200 líneas del log
    tmp=$(mktemp /tmp/cron_drupal_alert.XXXXXX)
    tail -n 200 "$LOG" > "$tmp" || true
    # intentar enviar alerta (si falla, escribir en log)
    "$VENV_PY" "$LOGDIR/enviar_alerta.py" --subject "[ALERTA] verificar_drupal falla (rc=$rc)" --body-file "$tmp" || echo "[ALERTA] fallo al enviar alerta (rc=$rc)" >> "$LOG"
    rm -f "$tmp"
  fi

  return $rc
}

main "$@"
