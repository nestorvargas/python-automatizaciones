#!/usr/bin/env python3
"""
enviar_alerta.py
Enviar un correo de alerta usando las variables del .env (mismas que usa verificar_drupal.py).
Uso:
  enviar_alerta.py --subject "Asunto" --body-file /ruta/a/archivo.txt
"""
import os
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv


def send_mail(subject: str, body: str, recipients: list[str]):
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    FROM = os.getenv("REMITENTE", SMTP_USER)

    if not recipients:
        raise RuntimeError("No recipients configured for alert")

    msg = MIMEMultipart()
    msg["From"] = FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    try:
        server.ehlo()
        if SMTP_PORT == 587:
            server.starttls()
            server.ehlo()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM, recipients, msg.as_string())
    finally:
        server.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args()

    load_dotenv()
    dests = [e.strip() for e in os.getenv("DESTINATARIOS", "").split(",") if e.strip()]
    if not dests:
        smtp_user = os.getenv("SMTP_USER", "")
        if smtp_user:
            dests = [smtp_user]

    with open(args.body_file, "r", encoding="utf-8", errors="ignore") as f:
        body = f.read()

    try:
        send_mail(args.subject, body, dests)
        print("Alerta enviada a:", ", ".join(dests))
    except Exception as e:
        print("ERROR enviando alerta:", e)
        raise


if __name__ == "__main__":
    main()
