#!/usr/bin/env python3
"""
scan_security_drupal.py
-----------------------
Escaneo básico remoto para sitios Drupal:
  - Intenta obtener la versión core desde /CHANGELOG.txt o meta generator
  - Busca rutas de módulos/temas expuestas en el HTML y trata de obtener sus CHANGELOG
  - Genera un reporte HTML sencillo en `seguridad_reporte.html`

Uso:
    .venv/bin/python automatizacion_python_cron_reports/scan_security_drupal.py

El script carga la lista `SITIOS` desde `verificar_drupal.py` si está disponible.
"""

from __future__ import annotations
import re
import time
import requests
from pathlib import Path
from datetime import datetime
import importlib.util
import sys
import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv


HERE = Path(__file__).parent
OUT_HTML = HERE / "seguridad_reporte.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DrupalSecurityScan/1.0; +https://colcomercio.com.co)"
}
TIMEOUT = 12


def load_verifier_module() -> object | None:
    mod_path = HERE / "verificar_drupal.py"
    if not mod_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("verificar_drupal", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_text(url: str, timeout: int = TIMEOUT) -> tuple[int | None, str | None, dict]:
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        return r.status_code, r.text, dict(r.headers)
    except requests.RequestException:
        return None, None, {}


def parse_core_version_from_changelog(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r"Drupal\s*(\d[\d.]*\d)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    # fallback: single version number like "Drupal 11"
    m = re.search(r"Drupal\s*(\d+)", text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_module_theme_paths(html: str | None) -> set[str]:
    if not html:
        return set()
    # Encuentra rutas que contengan /modules/... o /themes/...
    matches = re.findall(r'/(?:sites/[^\s"\']+/)?(?:modules|themes)/[^"\s<>]+' , html, re.IGNORECASE)
    bases = set()
    for m in matches:
        parts = m.strip("/").split("/")
        # keep up to modules/<module_name> or themes/<theme_name>
        try:
            idx = parts.index("modules")
        except ValueError:
            try:
                idx = parts.index("themes")
            except ValueError:
                continue
        base = "/" + "/".join(parts[: idx + 2])
        bases.add(base)
    return bases


def try_get_component_version(base_url: str, base_path: str) -> str | None:
    # base_path like '/sites/all/modules/views'
    urls = [
        f"{base_url.rstrip('/')}{base_path}/CHANGELOG.txt",
        f"{base_url.rstrip('/')}{base_path}/README.txt",
        f"{base_url.rstrip('/')}{base_path}/VERSION",
    ]
    for u in urls:
        status, text, _ = fetch_text(u)
        if status and status < 400 and text:
            # buscar versión sencilla
            m = re.search(r"(Version|Versi[oó]n|v)\s*[:]?\s*([\d.]+)", text, re.IGNORECASE)
            if m:
                return m.group(2)
            m2 = re.search(r"([\d]+\.[\d]+(?:\.[\d]+)?)", text)
            if m2:
                return m2.group(1)
            # si no encontramos versión explícita, devolvemos indicador de existencia
            return "present (no version)"
    return None


# Encabezados HTTP de seguridad que verificamos
SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-XSS-Protection",
]


def scan_site(url: str) -> dict:
    now = datetime.utcnow().isoformat()
    entry = {"url": url, "checked_at": now, "core_version": None, "components": {}, "security_headers": {}, "error": None}

    try:
        resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        status = resp.status_code
        html = resp.text
        resp_headers = resp.headers
    except requests.RequestException:
        status = None
        html = None
        resp_headers = {}

    if status is None:
        entry["error"] = "no response"
        return entry

    # Verificar encabezados de seguridad HTTP
    for h in SECURITY_HEADERS:
        entry["security_headers"][h] = resp_headers.get(h)

    # 1) intentar /CHANGELOG.txt (solo si devuelve texto plano, no HTML)
    ch_status, ch_text, ch_headers = fetch_text(url.rstrip("/") + "/CHANGELOG.txt")
    ct = ch_headers.get("Content-Type", "") if ch_headers else ""
    if ch_status and ch_status < 400 and "text/html" not in ct.lower():
        core_ver = parse_core_version_from_changelog(ch_text)
    else:
        core_ver = None
    if core_ver:
        entry["core_version"] = core_ver
    else:
        # intentar buscar meta generator
        m = re.search(r'<meta[^>]+name=["\']Generator["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m and "drupal" in m.group(1).lower():
            mv = re.search(r"Drupal\s*(\d[\d.]*\d)", m.group(1), re.IGNORECASE)
            if not mv:
                mv = re.search(r"Drupal\s*(\d+)", m.group(1), re.IGNORECASE)
            if mv:
                entry["core_version"] = mv.group(1)

    # 2) detectar módulos/temas expuestos y consultar sus CHANGELOG
    bases = extract_module_theme_paths(html)
    for b in sorted(bases):
        ver = try_get_component_version(url, b)
        entry["components"][b] = ver or "not accessible"

    return entry


def generate_html_report(results: list[dict]) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)
    with_core = sum(1 for r in results if r.get("core_version"))
    total_comps = sum(len(r.get("components", {})) for r in results)
    errors = sum(1 for r in results if r.get("error"))
    # Promedio de encabezados de seguridad presentes
    header_counts = [sum(1 for v in r.get("security_headers", {}).values() if v) for r in results if not r.get("error")]
    avg_headers = round(sum(header_counts) / len(header_counts), 1) if header_counts else 0
    total_sec_headers = len(SECURITY_HEADERS)

    # ── Construir filas: Sitio web | Estado | Resumen escaneo ──
    rows = ""
    for i, r in enumerate(results):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        url_escaped = r["url"]

        # Estado
        if r.get("error"):
            status_label = "No disponible"
            st_bg, st_border, st_color = "#fce8e6", "#ea4335", "#c5221f"
        else:
            status_label = "En l&iacute;nea"
            st_bg, st_border, st_color = "#e6f4ea", "#34a853", "#1e7e34"

        # Resumen de escaneo
        resumen_parts = []
        core = r.get("core_version")
        if core:
            resumen_parts.append(f"Core Drupal <b>{core}</b>")
        else:
            resumen_parts.append("Core: no detectado")

        comps = r.get("components", {})
        accessible = {k: v for k, v in comps.items() if v != "not accessible"}
        blocked = {k: v for k, v in comps.items() if v == "not accessible"}
        if accessible:
            resumen_parts.append(f"{len(accessible)} componente(s) expuesto(s)")
            for path, ver in sorted(accessible.items()):
                resumen_parts.append(f"&nbsp;&nbsp;&bull; {path}: {ver}")
        if blocked:
            resumen_parts.append(f"{len(blocked)} ruta(s) protegida(s) &#10004;")
        if not comps:
            resumen_parts.append("Sin componentes detectados")

        resumen_html = "<br>".join(resumen_parts)

        # Encabezados de seguridad
        sec_h = r.get("security_headers", {})
        present = sum(1 for v in sec_h.values() if v)
        missing = len(sec_h) - present
        if sec_h:
            if missing == 0:
                score_bg, score_color = "#e6f4ea", "#1e7e34"
            elif missing <= 2:
                score_bg, score_color = "#fef7e0", "#e37400"
            else:
                score_bg, score_color = "#fce8e6", "#c5221f"
            headers_parts = [f'<span style="background:{score_bg};color:{score_color};padding:2px 8px;border-radius:10px;font-weight:700;font-size:11px;">{present}/{len(sec_h)}</span>']
            for h_name in SECURITY_HEADERS:
                val = sec_h.get(h_name)
                if val:
                    headers_parts.append(f'<span style="color:#1e7e34;">&#10004;</span> <span style="font-size:11px;">{h_name}</span>')
                else:
                    headers_parts.append(f'<span style="color:#c5221f;">&#10008;</span> <span style="font-size:11px;color:#999;">{h_name}</span>')
            headers_html = "<br>".join(headers_parts)
        else:
            headers_html = '<span style="color:#999;font-size:11px;">Sin datos</span>'

        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:top;overflow:hidden;word-break:break-all;">'
            f'<a href="{url_escaped}" style="color:#1a73e8;text-decoration:none;font-size:13px;font-weight:500;">{url_escaped}</a></td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:top;padding-top:12px;">'
            f'<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;"><tr>'
            f'<td style="background:{st_bg};border:1px solid {st_border};border-radius:20px;padding:4px 14px;white-space:nowrap;">'
            f'<span style="color:{st_color};font-size:12px;font-weight:700;font-family:Arial,sans-serif;">&#9679;&nbsp; {status_label}</span>'
            f'</td></tr></table></td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:top;font-size:12px;line-height:1.6;color:#444;">'
            f'{resumen_html}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:top;font-size:12px;line-height:1.5;color:#444;">'
            f'{headers_html}</td>'
            f'</tr>'
        )

    # ── HTML propio (NO toca reporte_drupal.html) ──
    err_bg = "#fce8e6" if errors else "#e8f5e9"
    err_color = "#c5221f" if errors else "#2e7d32"
    hdr_bg = "#e6f4ea" if avg_headers >= total_sec_headers - 1 else "#fef7e0" if avg_headers >= total_sec_headers - 3 else "#fce8e6"
    hdr_color = "#1e7e34" if avg_headers >= total_sec_headers - 1 else "#e37400" if avg_headers >= total_sec_headers - 3 else "#c5221f"
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Reporte Seguridad — Drupal</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;color:#333;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="980" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#0f3460 0%,#16213e 60%,#1a1a2e 100%);padding:30px 35px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle;width:72px;">
                  <img src="logo_corbeta.svg" alt="Corbeta" style="height:56px;display:block;border:0;" />
                </td>
                <td style="vertical-align:middle;padding-left:16px;">
                                    <h1 style="margin:0;color:#031c42;font-size:20px;font-weight:700;letter-spacing:0.5px;">
                    &#128274; Escaneo de Seguridad &mdash; Sitios Drupal
                  </h1>
                  <p style="margin:6px 0 0;color:#a0aec0;font-size:13px;">
                    Generado el {fecha} &nbsp;|&nbsp; Colcomercio
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- TARJETAS RESUMEN -->
        <tr>
          <td style="padding:25px 35px 10px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="17%" align="center" style="background:#e8f5e9;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#2e7d32;">{total}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Sitios</div>
                </td>
                <td width="3%"></td>
                <td width="17%" align="center" style="background:#e3f2fd;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#1565c0;">{with_core}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Core detectado</div>
                </td>
                <td width="3%"></td>
                <td width="17%" align="center" style="background:#e8f0fe;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#1a56db;">{total_comps}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Componentes</div>
                </td>
                <td width="3%"></td>
                <td width="17%" align="center" style="background:{err_bg};border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:{err_color};">{errors}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Errores</div>
                </td>
                <td width="3%"></td>
                <td width="17%" align="center" style="background:{hdr_bg};border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:{hdr_color};">{avg_headers}/{total_sec_headers}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Headers prom.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- TABLA -->
        <tr>
          <td style="padding:20px 20px 30px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #e0e0e0;table-layout:fixed;">
              <colgroup>
                <col style="width:22%;">
                <col style="width:10%;">
                <col style="width:38%;">
                <col style="width:30%;">
              </colgroup>
              <thead>
                <tr style="background:#0f3460;">
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Sitio web</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Estado</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Resumen escaneo</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Encabezados</th>
                </tr>
              </thead>
              <tbody>
{rows}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f9fa;padding:16px 35px;border-top:1px solid #e0e0e0;text-align:center;">
            <p style="margin:0;font-size:11px;color:#9e9e9e;">
              Seguridad Drupal &nbsp;&middot;&nbsp; Colcomercio &nbsp;&middot;&nbsp;
              <a href="https://colcomercio.com.co" style="color:#1a73e8;text-decoration:none;">colcomercio.com.co</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>'''


def main():
    mod = load_verifier_module()
    if mod and hasattr(mod, "SITIOS"):
        sitios = getattr(mod, "SITIOS")
    else:
        print("No se encontró `verificar_drupal.py`; use la variable SITIOS local o cree el archivo.")
        sitios = []

    if not sitios:
        print("No hay sitios configurados en SITIOS. Agregue URLs en `verificar_drupal.py`.")
        return

    results = []
    for url in sitios:
        print(f"Escaneando {url} ...", end=" ")
        try:
            r = scan_site(url)
            results.append(r)
            print("OK")
        except Exception as e:
            print("ERROR", e)
            results.append({"url": url, "error": str(e), "components": {}, "core_version": None})
        time.sleep(0.6)

    html = generate_html_report(results)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Reporte escrito en: {OUT_HTML}")

    # Enviar el reporte por correo usando variables en .env
    try:
        # cargar .env: primero el del proyecto (si existe), luego el local junto al script
        load_dotenv(HERE.parent / ".env")
        load_dotenv(HERE / ".env")
        SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        SMTP_USER = os.getenv("SMTP_USER", "")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        FROM = os.getenv("REMITENTE", SMTP_USER)
        DESTS = [e.strip() for e in os.getenv("DESTINATARIOS", SMTP_USER).split(",") if e.strip()]

        subject = "[Automatización] Escaneo de seguridad — Drupal"
        body = html

        if not DESTS:
            print("No hay destinatarios configurados en .env (DESTINATARIOS). No se enviará correo.")
            return

        send_mail_with_logo(SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM, DESTS, subject, body)
        print("Correo enviado a:", DESTS)
    except Exception as e:
        print("Error al intentar enviar el correo:", e)


def send_mail_with_logo(smtp_server: str, smtp_port: int, smtp_user: str, smtp_password: str, from_addr: str, recipients: list, subject: str, body_html: str):
    """Envía HTML por correo con logo CID (mismo patrón que verificar_drupal.py)."""
    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"] = from_addr
    msg_root["To"] = ", ".join(recipients)

    msg_alt = MIMEMultipart("alternative")
    msg_root.attach(msg_alt)

    # plain fallback
    plain = re.sub(r"<[^>]+>", "", body_html).replace("&nbsp;", " ").replace("&amp;", "&").strip()
    msg_alt.attach(MIMEText(plain or "Ver mensaje en cliente HTML.", "plain", "utf-8"))

    # Buscar logo raster (JPG/PNG) — más compatible con clientes de correo
    jpg_path = HERE / "logo_corbeta.jpg"
    png_path = HERE / "logo_corbeta.png"
    html_final = body_html
    logo_src_pattern = re.compile(r'src=["\'][^"\']*logo_corbeta[^"\']*["\']', re.IGNORECASE)

    if png_path.exists() or jpg_path.exists():
        img_path = png_path if png_path.exists() else jpg_path
        try:
            with open(img_path, "rb") as f:
                img_data = f.read()
            cid = "logo_cid"
            if logo_src_pattern.search(body_html):
                html_final = logo_src_pattern.sub(f'src="cid:{cid}"', body_html, count=1)
            msg_alt.attach(MIMEText(html_final, "html", "utf-8"))
            mime_img = MIMEImage(img_data)
            mime_img.add_header("Content-ID", f"<{cid}>")
            mime_img.add_header("Content-Disposition", "inline", filename=img_path.name)
            msg_root.attach(mime_img)
        except Exception:
            msg_alt.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        msg_alt.attach(MIMEText(body_html, "html", "utf-8"))

    # Garantizar que siempre haya una parte HTML
    if not any(isinstance(p, MIMEText) and p.get_content_subtype() == "html" for p in msg_alt.get_payload()):
        msg_alt.attach(MIMEText(body_html, "html", "utf-8"))

    # Enviar con TLS (mismo patrón que verificar_drupal.py)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, recipients, msg_root.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        print(f"Error de autenticación SMTP ({exc.smtp_code}): {exc.smtp_error.decode(errors='replace')}")
        raise


if __name__ == '__main__':
    main()
