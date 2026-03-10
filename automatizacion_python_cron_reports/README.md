# automatizacion_python — Report site

Resumen

Este directorio contiene scripts para generar reportes automáticos:
- `verificar_sitios.py` — comprueba que los sitios listados estén en línea y valide el GTM.
- `verificar_drupal.py` — detecta uso de Drupal, versión, mantenimiento y tiempos de respuesta.

Dependencias

Las dependencias están en `requirements.txt`. Las principales son:
- `requests`
- `python-dotenv`
- `msal` (para `teams_report.py`)
- `tabulate` (salida de `teams_report.py`)

Wrapper para cron

Se añadió `run_cron_reports.sh`, un wrapper que activa el virtualenv (si existe) y ejecuta los scripts, dejando logs en:

- `cron.log` — salida de `verificar_sitios.py` y resumen final
- `cron_drupal.log` — salida de `verificar_drupal.py`

Ejemplo de entrada en `crontab` (abre con `crontab -e`):

```cron
# Ejecutar cada día a las 08:00
0 8 * * * cd /ruta/al/proyecto/curso-python/automatizacion_python_cron_reports && ./run_cron_reports.sh
```

Notas de seguridad

- `automatizacion_python_cron_reports/.env` contiene credenciales SMTP; asegúrate de que no esté versionado públicamente y añadirlo a `.gitignore` si corresponde.

Ejecución manual

```bash
cd automatizacion_python_cron_reports
python verificar_sitios.py
python verificar_drupal.py
```

Si quieres que actualice `requirements.txt` (por ejemplo fijar versiones o añadir una nueva dependencia) o que haga ejecutable `run_cron_reports.sh`, lo hago ahora.
