"""
verificar_sitios.py
-------------------
Revisa si una lista de sitios web está en línea y si cada uno tiene
el tag de Google Tag Manager (GTM) correcto. Al final envía un reporte
por correo electrónico.

Uso:
    python verificar_sitios.py

Configuración:
    Edita el archivo .env en la misma carpeta con las credenciales SMTP.
"""

import os
import re
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Carga variables de entorno desde .env
# ─────────────────────────────────────────────
load_dotenv()

SMTP_SERVER   = os.getenv("SMTP_SERVER", "mail.colcomercio.com.co")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "tu_correo@colcomercio.com.co")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "tu_contraseña")
REMITENTE     = os.getenv("REMITENTE", SMTP_USER)
# Destinatarios separados por coma
DESTINATARIOS = [e.strip() for e in os.getenv("DESTINATARIOS", "").split(",") if e.strip()]

# ─────────────────────────────────────────────
# Lista de sitios a verificar
# Formato: (url, gtm_esperado_o_None)
# ─────────────────────────────────────────────
SITIOS = [
    ("https://www.redcontigo.com.co/",              "GTM-MLQRHSHW"),
    ("https://www.midia.com.co",                    "GTM-P8MHNQ9"),
    ("https://narinenseslomaximo.com/",             "GTM-5BMTMBD"),
    ("https://pidetucita.alkomprar.com/",           None),
    ("https://serviciokalley.com/",                 "GTM-TXN9FPT"),
    ("https://www.serviciotcl.com.co/",             "GTM-WC9KWD4S"),
    ("https://www.corbetatextiles.com.co/",         "GTM-TMKNSH9"),
    ("https://www.kalleymovil.com.co/",             "GTM-TTPCLLB"),
    ("https://descargascolcomercio.com/",           "GTM-KMBHSCRT"),
    ("https://www.ganaconkalley.co/",               None),
    ("https://www.dongfengcorautosandino.com/",     "GTM-TQVBW2D3"),
    ("https://www.descargasakt.com/",               None),
]

TIMEOUT = 15  # segundos por solicitud

# ─────────────────────────────────────────────
# Lógica de verificación
# ─────────────────────────────────────────────

def verificar_sitio(url: str, gtm_esperado: str | None) -> dict:
    """Revisa si el sitio está en línea y si contiene el GTM correcto."""
    resultado = {
        "url":          url,
        "gtm_esperado": gtm_esperado,
        "en_linea":     False,
        "status_code":  None,
        "gtm_encontrado": [],
        "gtm_ok":       None,   # True / False / None (sin GTM esperado)
        "error":        None,
    }

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SiteChecker/1.0; "
                "+https://colcomercio.com.co)"
            )
        }
        resp = requests.get(url, timeout=TIMEOUT, headers=headers,
                            allow_redirects=True)
        resultado["status_code"] = resp.status_code
        resultado["en_linea"]    = resp.status_code < 400

        # Busca TODOS los GTM en el HTML
        gtm_tags = re.findall(r"GTM-[A-Z0-9]+", resp.text)
        resultado["gtm_encontrado"] = list(dict.fromkeys(gtm_tags))  # únicos

        if gtm_esperado:
            resultado["gtm_ok"] = gtm_esperado in resultado["gtm_encontrado"]

    except requests.exceptions.SSLError as exc:
        resultado["error"] = f"SSL Error: {exc}"
    except requests.exceptions.ConnectionError as exc:
        resultado["error"] = f"Conexión fallida: {exc}"
    except requests.exceptions.Timeout:
        resultado["error"] = "Tiempo de espera agotado"
    except requests.exceptions.RequestException as exc:
        resultado["error"] = f"Error: {exc}"

    return resultado


def verificar_todos() -> list[dict]:
    resultados = []
    for url, gtm in SITIOS:
        print(f"  Verificando {url} ...", end=" ", flush=True)
        r = verificar_sitio(url, gtm)
        estado = "✓" if r["en_linea"] else "✗"
        print(estado)
        resultados.append(r)
    return resultados


# ─────────────────────────────────────────────
# Generación del reporte HTML
# ─────────────────────────────────────────────

VERDE  = "#d4edda"
ROJO   = "#f8d7da"
AMARILLO = "#fff3cd"
GRIS   = "#e2e3e5"

def _color_fila(r: dict) -> str:
    if not r["en_linea"]:
        return ROJO
    if r["gtm_esperado"] and not r["gtm_ok"]:
        return AMARILLO
    return VERDE


def generar_html(resultados: list[dict], fecha: str) -> str:
    total   = len(resultados)
    online  = sum(1 for r in resultados if r["en_linea"])
    offline = total - online
    gtm_ok  = sum(1 for r in resultados if r["gtm_ok"] is True)
    gtm_mal = sum(1 for r in resultados if r["gtm_ok"] is False)

    filas = ""
    for i, r in enumerate(resultados):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"

        # ── Badge estado en línea ──────────────────────────────────────────
        if r["en_linea"]:
            badge_online = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;">'
                '<tr><td style="background:#e6f4ea;border:1px solid #34a853;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#1e7e34;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">'
                '&#9679;&nbsp; En l&iacute;nea</span></td></tr></table>'
            )
        else:
            detalle = r["status_code"] or r["error"] or "sin respuesta"
            # Trunca errores de conexión largos para que se vea limpio
            if isinstance(detalle, str) and len(detalle) > 55:
                detalle_corto = detalle[:52] + "..."
            else:
                detalle_corto = detalle
            badge_online = (
                '<div style="text-align:center;">'
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;margin:0 auto;">'
                '<tr><td style="background:#fce8e6;border:1px solid #ea4335;border-radius:20px;'
                'padding:4px 16px;white-space:nowrap;">'
                '<span style="color:#c5221f;font-size:12px;font-weight:700;font-family:Arial,sans-serif;">'
                '&#9679;&nbsp; Ca&iacute;do</span></td></tr></table>'
                f'<div style="margin-top:5px;font-size:10px;color:#999;font-family:Arial,sans-serif;'
                f'word-break:break-word;line-height:1.3;">{detalle_corto}</div>'
                '</div>'
            )

        # ── GTM esperado ───────────────────────────────────────────────────
        if r["gtm_esperado"]:
            gtm_exp = (
                f'<span style="display:inline-block;background:#e8f0fe;border:1px solid #4285f4;'
                f'border-radius:4px;padding:3px 8px;font-family:Consolas,monospace;'
                f'font-size:12px;color:#1a56db;letter-spacing:0.3px;">{r["gtm_esperado"]}</span>'
            )
        else:
            gtm_exp = '<span style="color:#bbb;font-size:13px;">&#8212;</span>'

        # ── GTM encontrado ─────────────────────────────────────────────────
        if r["gtm_encontrado"]:
            # Resalta en verde el que coincide, gris los demás
            partes = []
            for t in r["gtm_encontrado"]:
                if t == r["gtm_esperado"]:
                    partes.append(
                        f'<span style="display:inline-block;background:#e6f4ea;border:1px solid #34a853;'
                        f'border-radius:4px;padding:3px 8px;font-family:Consolas,monospace;'
                        f'font-size:12px;color:#1e7e34;letter-spacing:0.3px;">{t}</span>'
                    )
                else:
                    partes.append(
                        f'<span style="display:inline-block;background:#f1f3f4;border:1px solid #dadce0;'
                        f'border-radius:4px;padding:3px 8px;font-family:Consolas,monospace;'
                        f'font-size:12px;color:#555;letter-spacing:0.3px;">{t}</span>'
                    )
            gtm_enc = " ".join(partes)
        else:
            gtm_enc = '<span style="color:#bbb;font-style:italic;font-size:12px;">no detectado</span>'

        # ── Badge resultado GTM ────────────────────────────────────────────
        if r["gtm_esperado"] is None:
            badge_gtm = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;">'
                '<tr><td style="background:#f1f3f4;border:1px solid #dadce0;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#666;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">'
                'Sin GTM</span></td></tr></table>'
            )
        elif r["gtm_ok"]:
            badge_gtm = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;">'
                '<tr><td style="background:#e6f4ea;border:1px solid #34a853;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#1e7e34;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">'
                'Correcto</span></td></tr></table>'
            )
        else:
            badge_gtm = (
                '<table cellpadding="0" cellspacing="0" style="display:inline-table;">'
                '<tr><td style="background:#fef7e0;border:1px solid #f9ab00;border-radius:20px;'
                'padding:4px 14px;white-space:nowrap;">'
                '<span style="color:#b06000;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">'
                'Incorrecto</span></td></tr></table>'
            )

        url_display = r['url'].replace("https://", "").replace("http://", "").rstrip("/")
        filas += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:middle;overflow:hidden;word-break:break-all;">
                <a href="{r['url']}" style="color:#1a73e8;text-decoration:none;font-size:12px;font-weight:500;">{url_display}</a>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:top;padding-top:13px;">{badge_online}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:middle;">{gtm_exp}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;vertical-align:middle;word-break:break-all;">{gtm_enc}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8eaed;text-align:center;vertical-align:middle;">{badge_gtm}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Reporte de Sitios — Colcomercio</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;color:#333;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="860" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);padding:30px 35px;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px;">
              📊 Reporte de Verificación de Sitios Web
            </h1>
            <p style="margin:8px 0 0;color:#a0aec0;font-size:13px;">
              Generado el {fecha} &nbsp;|&nbsp; Colcomercio
            </p>
          </td>
        </tr>

        <!-- TARJETAS RESUMEN -->
        <tr>
          <td style="padding:25px 35px 10px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="24%" align="center" style="background:#e8f5e9;border-radius:10px;padding:16px 10px;margin:4px;">
                  <div style="font-size:28px;font-weight:800;color:#2e7d32;">{total}</div>
                  <div style="font-size:11px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Total sitios</div>
                </td>
                <td width="4%"></td>
                <td width="24%" align="center" style="background:#e3f2fd;border-radius:10px;padding:16px 10px;">
                  <div style="font-size:28px;font-weight:800;color:#1565c0;">{online}</div>
                  <div style="font-size:11px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">En línea</div>
                </td>
                <td width="4%"></td>
                <td width="24%" align="center" style="background:#{"fce4ec" if offline > 0 else "e8f5e9"};border-radius:10px;padding:16px 10px;">
                  <div style="font-size:28px;font-weight:800;color:#{"c62828" if offline > 0 else "2e7d32"};">{offline}</div>
                  <div style="font-size:11px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Caídos</div>
                </td>
                <td width="4%"></td>
                <td width="24%" align="center" style="background:#{"fff3e0" if gtm_mal > 0 else "e8f5e9"};border-radius:10px;padding:16px 10px;">
                  <div style="font-size:28px;font-weight:800;color:#{"e65100" if gtm_mal > 0 else "2e7d32"};">{gtm_mal}</div>
                  <div style="font-size:11px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">GTM incorrecto</div>
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
                <col style="width:26%;">
                <col style="width:16%;">
                <col style="width:14%;">
                <col style="width:28%;">
                <col style="width:16%;">
              </colgroup>
              <thead>
                <tr style="background:#1a1a2e;">
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Sitio web</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Estado</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">GTM Esperado</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">GTM Encontrado</th>
                  <th style="padding:11px 12px;color:#e0e0e0;font-size:11px;text-align:center;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">GTM OK</th>
                </tr>
              </thead>
              <tbody>{filas}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f9fa;padding:16px 35px;border-top:1px solid #e0e0e0;text-align:center;">
            <p style="margin:0;font-size:11px;color:#9e9e9e;">
              Generado: Desarrollo Drupal &nbsp;·&nbsp; Colcomercio &nbsp;·&nbsp;
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
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Reporte] Verificación de sitios web — {fecha}"
    msg["From"]    = REMITENTE
    # Soporta múltiples destinatarios
    msg["To"]      = ", ".join(DESTINATARIOS)

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
          server.ehlo()
          server.starttls(context=context)
          server.login(SMTP_USER, SMTP_PASSWORD)
          server.sendmail(REMITENTE, DESTINATARIOS, msg.as_string())
        print(f"\n✉️  Correo enviado a: {', '.join(DESTINATARIOS)}")
    except smtplib.SMTPAuthenticationError as exc:
        code, msg_detail = exc.smtp_code, exc.smtp_error.decode(errors="replace")
        print(f"\n❌ Error de autenticación SMTP ({code}): {msg_detail}")
        if "5.7.3" in msg_detail or "5.7.139" in msg_detail:
            print("   → SMTP AUTH está DESHABILITADO en el servidor. Pide al admin que lo habilite.")
        elif "5.7.8" in msg_detail:
            print("   → Contraseña incorrecta o se requiere contraseña de aplicación (MFA).")
        else:
            print("   → Revisa usuario, contraseña y configuración del tenant de Microsoft 365.")
    except smtplib.SMTPException as exc:
        print(f"\n❌ No se pudo enviar el correo: {exc}")


# ─────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────

def main():
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n🔍 Iniciando verificación — {fecha}\n")

    resultados = verificar_todos()
    html       = generar_html(resultados, fecha)

    # Guarda el reporte localmente como respaldo
    ruta_reporte = os.path.join(os.path.dirname(__file__), "ultimo_reporte.html")
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📄 Reporte guardado en: {ruta_reporte}")

    enviar_correo(html, fecha)


if __name__ == "__main__":
    main()
