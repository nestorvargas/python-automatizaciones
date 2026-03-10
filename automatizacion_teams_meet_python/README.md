# automatizacion_python — Report site

Resumen

Este directorio contiene `teams_report.py`, un script que usa Microsoft Graph para:
- listar eventos del calendario del usuario,
- detectar reuniones online (Teams) y
- descargar attendance reports y convertir attendanceRecords a CSV cuando estén disponibles.

Requisitos previos

- Registrar una aplicación en Azure AD (App registrations).
  - Obtener `Application (client) ID` → configurar como `MSFT_CLIENT_ID`.
  - (Opcional) especificar `Tenant ID` como `MSFT_TENANT_ID` para forzar tenant.
  - Permisos (delegated): `User.Read`, `Calendars.Read`, `OnlineMeetings.Read` o `OnlineMeetings.Read.All`.
  - Si usas Device Code, habilita "Allow public client flows" en Authentication.

Instalación rápida

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# editar .env y poner MSFT_CLIENT_ID (y opcional MSFT_TENANT_ID)
```

Uso

```bash
python teams_report.py --days 7 --out reporte_teams.json

# App-only (client credentials) — necesita MSFT_CLIENT_SECRET, MSFT_TENANT_ID y MSFT_USER en .env
# Requiere permisos de aplicación en Azure AD: Calendars.Read (Application) y OnlineMeetings.Read.All (Application) si corresponde.
python teams_report.py --days 7 --out reporte_teams.json
```


Salida

- JSON resumen: `reporte_teams.json` (por defecto). Contiene la lista de eventos consultados.
- Si hay attendance reports, se crean carpetas en `teams_reports/<meeting_id>/` con:
  - `report_<report_id>.json` (JSON del report)
  - `attendance_<report_id>.csv` (CSV con columnas: `displayName,userId,role,firstJoin,lastLeave,totalSeconds`)

Problemas comunes

- No aparecen attendance reports: revisa permisos de la app, políticas del tenant o que la reunión haya generado report.
- Errores de autenticación: asegurarse de que `MSFT_CLIENT_ID` es correcto y completar el Device Code según las instrucciones en consola.

Alternativas

- Si prefieres autenticación app-only (client credentials), puedo adaptar el script para usar `client_id` + `client_secret` y permisos de aplicación.

Archivos relevantes

- Script: `teams_report.py`
- Dependencias: `requirements.txt`
- Ejemplo de variables: `.env.example`

Más ayuda

Si quieres, adapto el script para subir los CSV a OneDrive/Google Drive o usar autenticación app-only.
