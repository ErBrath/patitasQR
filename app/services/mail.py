# app/services/mail.py
import os, base64, json, time, smtplib, requests
from email.message import EmailMessage
from flask import current_app

# ---------- SMTP (para local) ----------
def _send_via_smtp(to: str, subject: str, body: str) -> None:
    server  = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
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
        if use_tls: s.starttls()
        if user and pwd: s.login(user, pwd)
        s.send_message(msg)

# ---------- Gmail API (para Render) ----------
def _gmail_get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gmail token error {r.status_code}: {r.text}")
    return r.json()["access_token"]

def _send_via_gmail_api(to: str, subject: str, body: str) -> None:
    # Requiere vars de entorno y que el remitente esté en esa cuenta de Gmail
    client_id     = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    sender        = current_app.config.get("MAIL_DEFAULT_SENDER") 

    if not (client_id and client_secret and refresh_token and sender):
        raise RuntimeError("Faltan GOOGLE_CLIENT_ID/SECRET, GMAIL_REFRESH_TOKEN o MAIL_DEFAULT_SENDER")

    access_token = _gmail_get_access_token(client_id, client_secret, refresh_token)

    # Construye el MIME y codifícalo en base64url (raw)
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    r = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        data=json.dumps({"raw": raw}),
        timeout=20,
    )
    if r.status_code not in (200, 202):
        raise RuntimeError(f"Gmail send error {r.status_code}: {r.text}")

def send_email(to: str, subject: str, body: str) -> None:
    transport = (current_app.config.get("MAIL_TRANSPORT") or os.getenv("MAIL_TRANSPORT") or "smtp").lower()
    if transport == "gmail_api":
        return _send_via_gmail_api(to, subject, body)
    return _send_via_smtp(to, subject, body)

