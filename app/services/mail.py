# app/services/mail.py
import os
import smtplib
from email.message import EmailMessage
from flask import current_app
import requests

def _send_via_smtp(to: str, subject: str, body: str) -> None:
    server  = current_app.config.get("MAIL_SERVER")
    port    = int(current_app.config.get("MAIL_PORT", 587))
    use_tls = bool(current_app.config.get("MAIL_USE_TLS", True))
    user    = current_app.config.get("MAIL_USERNAME")
    pwd     = current_app.config.get("MAIL_PASSWORD")
    sender  = current_app.config.get("MAIL_DEFAULT_SENDER") or user or "no-reply@example.com"

    if not server:
        print(f"[EMAIL MOCK]\nFROM: {sender}\nTO: {to}\nSUBJECT: {subject}\n\n{body}")
        return

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(server, port, timeout=20) as s:
        if use_tls:
            s.starttls()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)

def _send_via_sendgrid(to: str, subject: str, body: str) -> None:
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        raise RuntimeError("Falta SENDGRID_API_KEY")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME") or "no-reply@example.com"
    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": sender},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        },
        timeout=20,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"SendGrid error {r.status_code}: {r.text}")

def _send_via_mailgun(to: str, subject: str, body: str) -> None:
    api_key = os.getenv("MAILGUN_API_KEY")
    domain  = os.getenv("MAILGUN_DOMAIN")  # p.ej. mg.tudominio.com
    if not (api_key and domain):
        raise RuntimeError("Faltan MAILGUN_API_KEY o MAILGUN_DOMAIN")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or f"no-reply@{domain}"
    r = requests.post(
        f"https://api.mailgun.net/v3/{domain}/messages",
        auth=("api", api_key),
        data={
            "from": sender,
            "to": [to],
            "subject": subject,
            "text": body,
        },
        timeout=20,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Mailgun error {r.status_code}: {r.text}")

def send_email(to: str, subject: str, body: str) -> None:
    transport = (current_app.config.get("MAIL_TRANSPORT") or os.getenv("MAIL_TRANSPORT") or "smtp").lower()
    if transport == "sendgrid":
        return _send_via_sendgrid(to, subject, body)
    if transport == "mailgun":
        return _send_via_mailgun(to, subject, body)
    return _send_via_smtp(to, subject, body)
