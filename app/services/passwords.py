import hmac, hashlib, string
from flask import current_app

def gen_temp_password_from_email(correo: str, length: int = 10) -> str:
    correo = (correo or "").strip().lower()
    secret = (current_app.config.get("TEMP_PWD_SECRET") or current_app.config["SECRET_KEY"]).encode()
    digest = hmac.new(secret, f"pwd:{correo}".encode(), hashlib.sha256).digest()
    alphabet = string.ascii_letters + string.digits
    base = "".join(alphabet[b % len(alphabet)] for b in digest)[:length]
    if not any(c.islower() for c in base): base = "a" + base[1:]
    if not any(c.isupper() for c in base): base = base[:-1] + "A"
    if not any(c.isdigit() for c in base): base += "7"
    if "!" not in base: base += "!"
    return base
