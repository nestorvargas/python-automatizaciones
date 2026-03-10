"""
teams_report.py

Script para obtener un reporte de reuniones de Microsoft Teams usando Microsoft Graph.

Funcionamiento básico:
- Autenticación interactiva con Device Code (MSAL Public Client).
- Consulta del calendario del usuario en un rango de fechas y listado de reuniones.
- Para reuniones con `onlineMeeting` intenta obtener `attendanceReports` si están disponibles.

Requisitos:
- Registrar una app en Azure AD y habilitar permisos delegados: `Calendars.Read`,
  `OnlineMeetings.Read.All` (o `OnlineMeetings.Read`), `User.Read`.
- Permitir flujo de dispositivo (public client) si usas Device Code.
- Establecer la variable de entorno `MSFT_CLIENT_ID` (obligatoria) y opcionalmente
  `MSFT_TENANT_ID`.

Uso:
  python teams_report.py --days 7 --out reporte.json

El script guarda un JSON con las reuniones y, cuando se puede, los attendance reports.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
from msal import PublicClientApplication, ConfidentialClientApplication
from tabulate import tabulate
import csv
from pathlib import Path


def load_config():
    load_dotenv()
    client_id = os.getenv("MSFT_CLIENT_ID")
    tenant_id = os.getenv("MSFT_TENANT_ID")  # opcional
    if not client_id:
        print("Error: configure la variable de entorno MSFT_CLIENT_ID (app registration client id).", file=sys.stderr)
        sys.exit(1)
    return client_id, tenant_id


def acquire_token(client_id, tenant_id, scopes):
    authority = f"https://login.microsoftonline.com/{tenant_id}" if tenant_id else "https://login.microsoftonline.com/common"
    app = PublicClientApplication(client_id=client_id, authority=authority)
    flow = app.initiate_device_flow(scopes=scopes)
    if "message" in flow:
        print(flow["message"])  # instrucciones para el usuario
    else:
        raise ValueError("No se pudo iniciar el device flow.")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise RuntimeError(f"Error en autenticación: {result.get('error_description') or result}")


def acquire_token_interactive(client_id, tenant_id, scopes):
    authority = f"https://login.microsoftonline.com/{tenant_id}" if tenant_id else "https://login.microsoftonline.com/common"
    app = PublicClientApplication(client_id=client_id, authority=authority)
    # Esto abrirá el navegador para que el usuario inicie sesión y conceda permisos.
    result = app.acquire_token_interactive(scopes=scopes)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise RuntimeError(f"Error en autenticación interactiva: {result.get('error_description') or result}")


def acquire_token_client_credentials(client_id, tenant_id, client_secret):
    if not tenant_id:
        raise ValueError("MSFT_TENANT_ID es obligatorio para client credentials")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = ConfidentialClientApplication(client_id=client_id, client_credential=client_secret, authority=authority)
    # usar el scope .default para app-only
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    else:
        raise RuntimeError(f"Error en client credentials: {result.get('error_description') or result}")


def isoformat(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()


def get_calendar_view(token, start_dt, end_dt):
    headers = {"Authorization": f"Bearer {token}", "Prefer": 'outlook.timezone="UTC"'}
    # Nota: si usamos app-only, se debe consultar el calendario de un usuario concreto.
    user = os.getenv("MSFT_USER")
    if user:
        url = f"https://graph.microsoft.com/v1.0/users/{user}/calendarView"
    else:
        url = "https://graph.microsoft.com/v1.0/me/calendarView"
    params = {
        "startDateTime": isoformat(start_dt),
        "endDateTime": isoformat(end_dt),
        "$select": "subject,organizer,start,end,attendees,onlineMeeting,onlineMeetingProvider,onlineMeetingUrl",
        "$orderby": "start/dateTime"
    }
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json().get("value", [])


def try_get_attendance_reports(token, meeting_id):
    headers = {"Authorization": f"Bearer {token}"}
    # Intentamos distintos endpoints comunes
    endpoints = [
        f"https://graph.microsoft.com/v1.0/me/onlineMeetings/{meeting_id}/attendanceReports",
        f"https://graph.microsoft.com/v1.0/users/me/onlineMeetings/{meeting_id}/attendanceReports",
        f"https://graph.microsoft.com/v1.0/communications/onlineMeetings/{meeting_id}/attendanceReports"
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                return r.json().get("value", [])
            # si 404 o 403, continuamos intentando otras rutas
        except requests.RequestException:
            continue
    return None


def try_get_attendance_records(token, meeting_id, report_id):
    """Intentar obtener attendanceRecords para un attendanceReport concreto.
    Devuelve la lista de registros o None.
    """
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        f"https://graph.microsoft.com/v1.0/communications/onlineMeetings/{meeting_id}/attendanceReports/{report_id}/attendanceRecords",
        f"https://graph.microsoft.com/v1.0/me/onlineMeetings/{meeting_id}/attendanceReports/{report_id}/attendanceRecords",
        f"https://graph.microsoft.com/v1.0/users/me/onlineMeetings/{meeting_id}/attendanceReports/{report_id}/attendanceRecords",
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                return r.json().get("value", [])
        except requests.RequestException:
            continue
    return None


def save_attendance_records_csv(records, outpath: Path):
    """Convertir una lista de attendanceRecords en CSV con columnas útiles."""
    if not records:
        return False
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with outpath.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["displayName", "userId", "role", "firstJoin", "lastLeave", "totalSeconds"])
        for rec in records:
            identity = rec.get("identity") or {}
            display = identity.get("user", {}).get("displayName") or identity.get("displayName") or rec.get("displayName")
            user_id = identity.get("user", {}).get("id") or identity.get("id") or ""
            role = rec.get("role") or ""
            intervals = rec.get("attendanceIntervals") or rec.get("attendanceIntervals", [])
            first_join = ""
            last_leave = ""
            total = 0
            for it in intervals:
                j = it.get("joinDateTime")
                l = it.get("leaveDateTime")
                if j and not first_join:
                    first_join = j
                if l:
                    last_leave = l
                try:
                    if j and l:
                        dt_j = datetime.fromisoformat(j.replace('Z', '+00:00'))
                        dt_l = datetime.fromisoformat(l.replace('Z', '+00:00'))
                        total += int((dt_l - dt_j).total_seconds())
                except Exception:
                    pass
            writer.writerow([display, user_id, role, first_join, last_leave, total])
    return True


def main():
    parser = argparse.ArgumentParser(description="Obtener reporte de reuniones Teams usando Microsoft Graph.")
    parser.add_argument("--days", type=int, default=7, help="Cuántos días atrás buscar (default 7)")
    parser.add_argument("--out", type=str, default="teams_report.json", help="Archivo de salida JSON")
    args = parser.parse_args()

    client_id, tenant_id = load_config()
    # Soporta tres modos de autenticación:
    # - Si MSFT_CLIENT_SECRET está presente: client credentials (app-only). Requiere MSFT_TENANT_ID y opcional MSFT_USER.
    # - Si MSFT_USE_INTERACTIVE=1: flujo interactivo en navegador (delegated)
    # - En caso contrario: Device Code (delegated)
    client_secret = os.getenv("MSFT_CLIENT_SECRET")
    use_interactive = os.getenv("MSFT_USE_INTERACTIVE", "0") in ("1", "true", "True", "yes", "y")
    if client_secret:
        # app-only
        token = acquire_token_client_credentials(client_id, tenant_id, client_secret)
    else:
        scopes = [
            "User.Read",
            "Calendars.Read",
            "OnlineMeetings.Read",
            "OnlineMeetings.Read.All"
        ]
        if use_interactive:
            token = acquire_token_interactive(client_id, tenant_id, scopes)
        else:
            token = acquire_token(client_id, tenant_id, scopes)

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=args.days)

    print(f"Consultando calendario desde {start_dt.isoformat()} hasta {end_dt.isoformat()}")
    events = get_calendar_view(token, start_dt, end_dt)
    results = []

    for ev in events:
        item = {
            "subject": ev.get("subject"),
            "start": ev.get("start"),
            "end": ev.get("end"),
            "organizer": ev.get("organizer"),
            "attendees": ev.get("attendees", []),
            "onlineMeeting": ev.get("onlineMeeting")
        }
        # intentar obtener attendance reports si existe onlineMeeting y su id
        om = ev.get("onlineMeeting")
        meeting_id = None
        if isinstance(om, dict):
            meeting_id = om.get("id")
            # algunos eventos no exponen 'id' en onlineMeeting, intentamos extraer de joinUrl
            if not meeting_id and om.get("joinUrl"):
                # no garantizado — dejamos None
                meeting_id = None

        if meeting_id:
            reports = try_get_attendance_reports(token, meeting_id)
            item["attendanceReports"] = reports
            # si hay reports, guardarlos y tratar de obtener attendanceRecords
            if reports:
                base_dir = Path("teams_reports")
                meeting_dir = base_dir / (meeting_id or "unknown_meeting")
                meeting_dir.mkdir(parents=True, exist_ok=True)
                for rep in reports:
                    rep_id = rep.get("id") or rep.get("reportId") or "unknown_report"
                    # guardar JSON del report
                    rep_json_path = meeting_dir / f"report_{rep_id}.json"
                    with rep_json_path.open("w", encoding="utf-8") as rf:
                        json.dump(rep, rf, ensure_ascii=False, indent=2)
                    # intentar obtener attendanceRecords y guardarlos en CSV
                    records = try_get_attendance_records(token, meeting_id, rep_id)
                    if records:
                        csv_path = meeting_dir / f"attendance_{rep_id}.csv"
                        saved = save_attendance_records_csv(records, csv_path)
                        if saved:
                            print(f"Guardado attendance CSV: {csv_path}")
        else:
            item["attendanceReports"] = None

        results.append(item)

    # Guardar salida
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"query": {"start": start_dt.isoformat(), "end": end_dt.isoformat()}, "meetings": results}, f, ensure_ascii=False, indent=2)

    # Mostrar resumen sencillo en consola
    table = []
    for r in results:
        table.append([r.get("subject"), r.get("start", {}).get("dateTime"), len(r.get("attendees", [])), "sí" if r.get("attendanceReports") else "no"])
    print(tabulate(table, headers=["Asunto", "Inicio (UTC)", "#Asistentes previstos", "AttendanceReport"]))
    print(f"Guardado: {args.out}")


if __name__ == "__main__":
    main()
