# Automatizaciones — Reportes y verificaciones

Este repo contiene scripts para verificar sitios (Drupal y otros), generar
reportes HTML y enviar notificaciones por correo. Está pensado para ejecutarse
en un entorno virtual y desde cron.

Estructura principal:
- `automatizacion_python_cron_reports/` — scripts de verificación y plantillas HTML.
- `automatizacion_teams_meet_python/` — scripts de reportes de Teams (separado).
- `modulo1.py` — ejemplo antiguo (no necesario para la automatización).

Requisitos:
- Python 3.8+
- `pip install -r automatizacion_python_cron_reports/requirements.txt` (si existe)

Instalación rápida (recomendada):

```bash
cd /ruta/al/proyecto
python -m venv .venv
source .venv/bin/activate
pip install -r automatizacion_python_cron_reports/requirements.txt
```

Variables de entorno:
- Copia y edita `automatizacion_python_cron_reports/.env` con tus credenciales SMTP:
	- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
	- `REMITENTE`, `DESTINATARIOS` (comas separan múltiples destinatarios)

Ejecutar manualmente (prueba):

```bash
source .venv/bin/activate
python automatizacion_python_cron_reports/verificar_drupal.py
```

Cron (ejemplo para ejecutar diariamente a las 08:00):

```cron
0 8 * * * cd /Users/tuusuario/…/curso-python && ./automatizacion_python_cron_reports/run_verificar_drupal.sh
```

Notas operativas:
- Los reportes HTML se generan en `automatizacion_python_cron_reports/reporte_drupal.html`.
- El script intenta insertar el logo del proyecto desde `automatizacion_python_cron_reports/logo_corbeta.jpg` (o SVG). Si existe, lo adjunta inline para máxima compatibilidad.
- Hay un wrapper `run_verificar_drupal.sh` que hace rotación de logs y llama a `verificar_drupal.py`.

Control de versiones:
- Trabajo en la rama `feature/logo-email`. Se creó un remoto `origin` apuntando a tu repo.


