import smtplib
from email.message import EmailMessage
from flask import current_app

def send_email(to: str, subject: str, body: str) -> None:
    server = current_app.config.get("MAIL_SERVER")
    if not server:
        print(f"[EMAIL MOCK]\nTO: {to}\nSUBJECT: {subject}\n\n{body}")
        return
    msg = EmailMessage()
    msg["From"] = current_app.config.get("MAIL_DEFAULT_SENDER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(server, current_app.config.get("MAIL_PORT", 587)) as s:
        if current_app.config.get("MAIL_USE_TLS", True):
            s.starttls()
        user = current_app.config.get("MAIL_USERNAME")
        pwd = current_app.config.get("MAIL_PASSWORD")
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)
