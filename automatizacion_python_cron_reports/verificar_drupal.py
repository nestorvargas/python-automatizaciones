"""
verificar_drupal.py
--------------------
Verifica los sitios web para detectar:
  - Si el sitio está en línea
  - Si usa Drupal y qué versión
  - Si está en modo mantenimiento
  - Tiempo de respuesta en ms

Al finalizar envía un reporte HTML por correo electrónico.

Uso:
    python verificar_drupal.py

Configuración:
    Usa el mismo .env que verificar_sitios.py
"""

#!/usr/bin/env python3

import os
import re
import smtplib
import ssl
import time
from datetime import datetime
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders

import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Variables de entorno
# ─────────────────────────────────────────────
load_dotenv()

SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REMITENTE     = os.getenv("REMITENTE", SMTP_USER)
# Destinatarios separados por coma
DESTINATARIOS = [e.strip() for e in os.getenv("DESTINATARIOS", "").split(",") if e.strip()]

TIMEOUT = 15

# ─────────────────────────────────────────────
# Sitios a verificar (los mismos del reporte GTM)
# ─────────────────────────────────────────────
SITIOS = [
    "https://www.redcontigo.com.co/",
    "https://www.midia.com.co",
    "https://narinenseslomaximo.com/",
    "https://pidetucita.alkomprar.com/",
    "https://serviciokalley.com/",
    "https://www.serviciotcl.com.co/",
    "https://www.corbetatextiles.com.co/",
    "https://www.kalleymovil.com.co/",
    "https://descargascolcomercio.com/",
    "https://www.ganaconkalley.co/",
    "https://www.dongfengcorautosandino.com/",
    "https://www.descargasakt.com/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DrupalChecker/1.0; "
        "+https://colcomercio.com.co)"
    )
}

# Patrones de mantenimiento de Drupal
MAINT_PATTERNS = [
    r'id=["\']maintenance-page["\']',
    r'class=["\'][^"\']*maintenance-page[^"\']*["\']',
    r'site is currently under maintenance',
    r'sitio.*mantenimiento',
    r'<title>[^<]*mantenimiento[^<]*</title>',
    r'drupal-maintenance',
]


# ─────────────────────────────────────────────
# Lógica de verificación
# ─────────────────────────────────────────────

def detectar_drupal(html: str, headers_resp: dict) -> tuple[bool, str | None]:
    """Retorna (es_drupal, version_o_None)."""
    # 1. Cabecera X-Generator
    gen = headers_resp.get("X-Generator", "")
    if "drupal" in gen.lower():
        m = re.search(r"Drupal\s*([\d.]+)", gen, re.IGNORECASE)
        return True, m.group(1) if m else "desconocida"

    # 2. Meta generator en HTML
    m = re.search(
        r'<meta[^>]+name=["\']Generator["\'][^>]+content=["\']Drupal\s*([\d.]*)',
        html, re.IGNORECASE
    )
    if m:
        ver = m.group(1).strip() or "desconocida"
        return True, ver

    # 3. Rutas típicas de Drupal en el HTML
    drupal_signals = [
        r"/sites/default/files/",
        r"/sites/all/themes/",
        r"/core/themes/",          # Drupal 8+
        r"Drupal\.settings",
        r"drupalSettings",
        r"/modules/contrib/",
        r"/profiles/standard/",
    ]
    for pattern in drupal_signals:
        if re.search(pattern, html):
            return True, None   # Drupal pero versión no determinada

    return False, None


def detectar_mantenimiento(html: str, status_code: int) -> bool:
    """Detecta si el sitio está en modo mantenimiento."""
    if status_code == 503:
        return True
    html_lower = html.lower()
    for pattern in MAINT_PATTERNS:
        if re.search(pattern, html_lower, re.IGNORECASE):
            return True
    return False


def verificar_sitio(url: str) -> dict:
    resultado = {
        "url":           url,
        "en_linea":      False,
        "status_code":   None,
        "tiempo_ms":     None,
        "es_drupal":     False,
        "version":       None,
        "mantenimiento": False,
        "error":         None,
    }

    try:
        inicio = time.monotonic()
        resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS,
                            allow_redirects=True)
        resultado["tiempo_ms"]   = round((time.monotonic() - inicio) * 1000)
        resultado["status_code"] = resp.status_code
        resultado["en_linea"]    = resp.status_code < 400

        es_drupal, version = detectar_drupal(resp.text, dict(resp.headers))
        resultado["es_drupal"] = es_drupal
        resultado["version"]   = version

        resultado["mantenimiento"] = detectar_mantenimiento(
            resp.text, resp.status_code
        )

    except requests.exceptions.SSLError as exc:
        resultado["error"] = f"SSL Error: {exc}"
    except requests.exceptions.ConnectionError as exc:
        resultado["error"] = "Conexión fallida"
    except requests.exceptions.Timeout:
        resultado["error"] = "Tiempo de espera agotado"
    except requests.exceptions.RequestException as exc:
        resultado["error"] = str(exc)[:80]

    return resultado


def verificar_todos() -> list[dict]:
    resultados = []
    for url in SITIOS:
        print(f"  Verificando {url} ...", end=" ", flush=True)
        r = verificar_sitio(url)
        icono = "✓" if r["en_linea"] else "✗"
        print(icono)
        resultados.append(r)
    return resultados


# ─────────────────────────────────────────────
# Generación del reporte HTML
# ─────────────────────────────────────────────

def _tiempo_badge(ms: int | None) -> str:
    if ms is None:
        return '<span style="color:#bbb;">—</span>'
    if ms < 800:
        color_bg, color_text, color_border = "#e6f4ea", "#1e7e34", "#34a853"
    elif ms < 2000:
        color_bg, color_text, color_border = "#fef7e0", "#b06000", "#f9ab00"
    else:
        color_bg, color_text, color_border = "#fce8e6", "#c5221f", "#ea4335"
    return (
        f'<span style="display:inline-block;background:{color_bg};border:1px solid {color_border};'
        f'border-radius:20px;padding:3px 10px;font-size:11px;font-weight:600;'
        f'font-family:Arial,sans-serif;color:{color_text};white-space:nowrap;">'
        f'{ms} ms</span>'
    )


def generar_html(resultados: list[dict], fecha: str) -> str:
    total       = len(resultados)
    online      = sum(1 for r in resultados if r["en_linea"])
    offline     = total - online
    con_drupal  = sum(1 for r in resultados if r["es_drupal"])
    en_maint    = sum(1 for r in resultados if r["mantenimiento"])

    filas = ""
    for i, r in enumerate(resultados):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"

        # ── Estado en línea ────────────────────────────────────────────────
        if r["en_linea"]:
            badge_online = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#e6f4ea;border:1px solid #34a853;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#1e7e34;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                '&#9679;&nbsp; En l&iacute;nea</span></td></tr></table>'
            )
        else:
            detalle = r["status_code"] or r["error"] or "sin respuesta"
            badge_online = (
                '<div style="text-align:center;">'
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#fce8e6;border:1px solid #ea4335;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#c5221f;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                '&#9679;&nbsp; Ca&iacute;do</span></td></tr></table>'
                f'<div style="margin-top:5px;font-size:10px;color:#999;font-family:Arial,sans-serif;">'
                f'{detalle}</div></div>'
            )

        # ── Drupal ─────────────────────────────────────────────────────────
        if not r["en_linea"]:
            badge_drupal = '<span style="color:#bbb;">—</span>'
        elif r["es_drupal"]:
            ver_txt = f"v{r['version']}" if r["version"] else "versión no detectada"
            badge_drupal = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#e8f0fe;border:1px solid #4285f4;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                f'<span style="color:#1a56db;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                f'Drupal &nbsp;<span style="font-weight:400;font-size:11px;">{ver_txt}</span>'
                '</span></td></tr></table>'
            )
        else:
            badge_drupal = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#f1f3f4;border:1px solid #dadce0;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#777;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">'
                'No Drupal</span></td></tr></table>'
            )

        # ── Mantenimiento ──────────────────────────────────────────────────
        if not r["en_linea"]:
            badge_maint = '<span style="color:#bbb;">—</span>'
        elif r["mantenimiento"]:
            badge_maint = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#fef7e0;border:1px solid #f9ab00;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#b06000;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                '&#9888;&nbsp; Mantenimiento</span></td></tr></table>'
            )
        else:
            badge_maint = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#e6f4ea;border:1px solid #34a853;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#1e7e34;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                'Funcional</span></td></tr></table>'
            )

        tiempo_badge = _tiempo_badge(r["tiempo_ms"])
        url_display  = r["url"].replace("https://", "").replace("http://", "").rstrip("/")

        filas += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:middle;overflow:hidden;word-break:break-all;">
                <a href="{r['url']}" style="color:#1a73e8;text-decoration:none;font-size:12px;font-weight:500;">{url_display}</a>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:top;padding-top:13px;">{badge_online}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:middle;">{badge_drupal}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:middle;">{badge_maint}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:middle;">{tiempo_badge}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Reporte Drupal — Colcomercio</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;color:#333;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="980" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#0f3460 0%,#16213e 60%,#1a1a2e 100%);padding:30px 35px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle;width:72px;">
                  <img src="logo_corbeta.svg" alt="Corbeta" style="height:56px;display:block;border:0;" />
                </td>
                <td style="vertical-align:middle;padding-left:16px;">
                  <h1 style="margin:0;color:#1565c0;font-size:22px;font-weight:700;letter-spacing:0.5px;">
                    🔧 Reporte de Estado — Sitios Drupal
                  </h1>
                  <p style="margin:8px 0 0;color:#a0aec0;font-size:13px;">
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
                <td width="18%" align="center" style="background:#e8f5e9;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#2e7d32;">{total}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Total</div>
                </td>
                <td width="2%"></td>
                <td width="18%" align="center" style="background:#e3f2fd;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#1565c0;">{online}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">En l&iacute;nea</div>
                </td>
                <td width="2%"></td>
                <td width="18%" align="center" style="background:#{"fce4ec" if offline > 0 else "e8f5e9"};border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#{"c62828" if offline > 0 else "2e7d32"};">{offline}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Ca&iacute;dos</div>
                </td>
                <td width="2%"></td>
                <td width="18%" align="center" style="background:#e8f0fe;border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#1a56db;">{con_drupal}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Drupal</div>
                </td>
                <td width="2%"></td>
                <td width="18%" align="center" style="background:#{"fef7e0" if en_maint > 0 else "e8f5e9"};border-radius:10px;padding:16px 8px;">
                  <div style="font-size:28px;font-weight:800;color:#{"b06000" if en_maint > 0 else "2e7d32"};">{en_maint}</div>
                  <div style="font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Mant.</div>
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
                <col style="width:30%;">
                <col style="width:16%;">
                <col style="width:20%;">
                <col style="width:20%;">
                <col style="width:14%;">
              </colgroup>
              <thead>
                <tr style="background:#0f3460;">
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Sitio web</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Estado</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Plataforma</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Funcionalidad</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Respuesta</th>
                </tr>
              </thead>
              <tbody>{filas}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- LEYENDA -->
        <tr>
          <td style="padding:0 20px 20px;">
            <table cellpadding="0" cellspacing="0" style="background:#f8f9fa;border-radius:8px;border:1px solid #e0e0e0;width:100%;">
              <tr>
                <td style="padding:12px 16px;">
                  <span style="font-size:11px;color:#666;font-family:Arial,sans-serif;">
                    <strong>Tiempo de respuesta:</strong> &nbsp;
                    <span style="background:#e6f4ea;border:1px solid #34a853;border-radius:10px;padding:2px 8px;color:#1e7e34;font-size:10px;">&#60; 800 ms — R&aacute;pido</span> &nbsp;
                    <span style="background:#fef7e0;border:1px solid #f9ab00;border-radius:10px;padding:2px 8px;color:#b06000;font-size:10px;">800–2000 ms — Normal</span> &nbsp;
                    <span style="background:#fce8e6;border:1px solid #ea4335;border-radius:10px;padding:2px 8px;color:#c5221f;font-size:10px;">&#62; 2000 ms — Lento</span>
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f9fa;padding:16px 35px;border-top:1px solid #e0e0e0;text-align:center;">
            <p style="margin:0;font-size:11px;color:#9e9e9e;">
              Generado: Drupal Desarrollo &nbsp;&middot;&nbsp; Colcomercio &nbsp;&middot;&nbsp;
              <a href="https://colcomercio.com.co" style="color:#1a73e8;text-decoration:none;">colcomercio.com.co</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


# ─────────────────────────────────────────────
# Envío de correo
# ─────────────────────────────────────────────

def enviar_correo(html_body: str, fecha: str):
  # Preparar mensaje multipart/related para poder incluir imagen inline
  msg_root = MIMEMultipart("related")
  msg_root["Subject"] = f"[Reporte Drupal] Estado de sitios — {fecha}"
  msg_root["From"] = REMITENTE
  msg_root["To"] = ", ".join(DESTINATARIOS) if DESTINATARIOS else ""

  # Parte alternative (texto/html)
  msg_alternative = MIMEMultipart("alternative")
  msg_root.attach(msg_alternative)

  # Intentar localizar logo en la misma carpeta del script
  base_dir = os.path.dirname(__file__)
  svg_embedded_path = os.path.join(base_dir, "logo_corbeta_embedded.svg")
  svg_vector_path = os.path.join(base_dir, "logo_corbeta_vector.svg")
  svg_path = os.path.join(base_dir, "logo_corbeta.svg")
  png_path = os.path.join(base_dir, "logo_corbeta.png")
  jpg_path = os.path.join(base_dir, "logo_corbeta.jpg")

  html_with_logo = html_body
  # Priorizar imágenes raster (PNG/JPG) adjuntas por CID — más compatibles con clientes de correo
  if os.path.exists(png_path) or os.path.exists(jpg_path):
    img_path = png_path if os.path.exists(png_path) else jpg_path
    try:
      with open(img_path, "rb") as f:
        img_data = f.read()
      # preparar alternative parts
      msg_text = MIMEText("Adjunto: logo en correo.", "plain", "utf-8")
      msg_alternative.attach(msg_text)
      # html con cid: reemplazar el src del logo existente en la plantilla
      cid = "logo_cid"
      # buscar y reemplazar src que apunte a logo_corbeta.* (svg/png/jpg)
      logo_src_pattern = re.compile(r'src=["\"][^"\"]*logo_corbeta[^"\"]*["\"]', re.IGNORECASE)
      if logo_src_pattern.search(html_body):
        html_with_logo = logo_src_pattern.sub(f'src="cid:{cid}"', html_body, count=1)
      else:
        # fallback: insertar imagen justo después de <body>
        img_tag = f'<div style="padding:8px 0;text-align:left;"><img src="cid:{cid}" alt="logo" style="height:56px;display:block;border:0;"/></div>'
        html_with_logo = re.sub(r"(<body[^>]*>)", r"\1" + img_tag, html_body, count=1, flags=re.IGNORECASE)
      msg_html = MIMEText(html_with_logo, "html", "utf-8")
      msg_alternative.attach(msg_html)
      mime_img = MIMEImage(img_data)
      mime_img.add_header("Content-ID", f"<{cid}>")
      mime_img.add_header("Content-Disposition", "inline", filename=os.path.basename(img_path))
      msg_root.attach(mime_img)
    except Exception:
      msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))
  # Si no hay PNG/JPG, intentar SVG embebido
  elif os.path.exists(svg_embedded_path):
    try:
      with open(svg_embedded_path, "rb") as f:
        svg_b = f.read()
      svg_b64 = base64.b64encode(svg_b).decode("ascii")
      # reemplazar ruta del logo por data URI
      logo_src_pattern = re.compile(r'src=["\"][^"\"]*logo_corbeta[^"\"]*["\"]', re.IGNORECASE)
      data_uri = f'data:image/svg+xml;base64,{svg_b64}'
      if logo_src_pattern.search(html_body):
        html_with_logo = logo_src_pattern.sub(f'src="{data_uri}"', html_body, count=1)
      else:
        img_tag = f'<div style="padding:8px 0;text-align:left;"><img src="{data_uri}" alt="logo" style="height:56px;display:block;border:0;"/></div>'
        html_with_logo = re.sub(r"(<body[^>]*>)", r"\1" + img_tag, html_body, count=1, flags=re.IGNORECASE)
      msg_alternative.attach(MIMEText(html_with_logo, "html", "utf-8"))
    except Exception:
      msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))
  elif os.path.exists(svg_path) or os.path.exists(svg_vector_path):
    svg_file = svg_path if os.path.exists(svg_path) else svg_vector_path
    try:
      with open(svg_file, "rb") as f:
        svg_b = f.read()
      svg_b64 = base64.b64encode(svg_b).decode("ascii")
      logo_src_pattern = re.compile(r'src=["\"][^"\"]*logo_corbeta[^"\"]*["\"]', re.IGNORECASE)
      data_uri = f'data:image/svg+xml;base64,{svg_b64}'
      if logo_src_pattern.search(html_body):
        html_with_logo = logo_src_pattern.sub(f'src="{data_uri}"', html_body, count=1)
      else:
        img_tag = f'<div style="padding:8px 0;text-align:left;"><img src="{data_uri}" alt="logo" style="height:56px;display:block;border:0;"/></div>'
        html_with_logo = re.sub(r"(<body[^>]*>)", r"\1" + img_tag, html_body, count=1, flags=re.IGNORECASE)
      msg_alternative.attach(MIMEText(html_with_logo, "html", "utf-8"))
    except Exception:
      msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))
  else:
    # Ningún logo disponible; adjuntar HTML tal cual
    msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))

  # Si no se adjuntó HTML aún (caso SVG embebido o fallback), asegurarse de añadirlo
  if not any(isinstance(part, MIMEText) and part.get_content_subtype() == "html" for part in msg_alternative.get_payload()):
    msg_alternative.attach(MIMEText(html_with_logo, "html", "utf-8"))

  context = ssl.create_default_context()
  try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
      server.ehlo()
      server.starttls(context=context)
      server.login(SMTP_USER, SMTP_PASSWORD)
      server.sendmail(REMITENTE, DESTINATARIOS if DESTINATARIOS else [], msg_root.as_string())
    print(f"\n✉️  Correo enviado a: {', '.join(DESTINATARIOS)}")
  except smtplib.SMTPAuthenticationError as exc:
    code = exc.smtp_code
    detail = exc.smtp_error.decode(errors="replace")
    print(f"\n❌ Error de autenticación SMTP ({code}): {detail}")
  except smtplib.SMTPException as exc:
    print(f"\n❌ No se pudo enviar el correo: {exc}")


# ─────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────

def main():
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n🔧 Verificación Drupal — {fecha}\n")

    resultados = verificar_todos()
    html       = generar_html(resultados, fecha)

    ruta = os.path.join(os.path.dirname(__file__), "reporte_drupal.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📄 Reporte guardado en: {ruta}")

    enviar_correo(html, fecha)


if __name__ == "__main__":
    main()
