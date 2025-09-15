# app/blueprints/passwords.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from itsdangerous import SignatureExpired, BadSignature
from .. import db
from ..models import Usuario
from ..services.passwords import gen_temp_password_from_email
from ..services.token import reset_serializer
from ..services.mail import send_email

bp = Blueprint("passwords", __name__)

# ruta para cambiar la contraseña, usuario recien creado
@bp.get("/cambiar-password")
@login_required
def cambiar_password():
    return render_template("change_password.html")

# Procesar cambio de contraseña usuario recien creado
@bp.post("/cambiar-password")
@login_required
def cambiar_password_post():
    actual = request.form.get("actual") or ""
    nueva = request.form.get("nueva") or ""
    repetir = request.form.get("repetir") or ""

    ok_actual = current_user.check_password(actual) or (actual == gen_temp_password_from_email(current_user.correo))
    if not ok_actual:
        flash("La contraseña actual no es correcta.", "error")
        return redirect(url_for("passwords.cambiar_password"))
    if len(nueva) < 8:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("passwords.cambiar_password"))
    if nueva != repetir:
        flash("La confirmación no coincide.", "error")
        return redirect(url_for("passwords.cambiar_password"))
    if nueva == actual:
        flash("La nueva contraseña debe ser distinta a la actual.", "error")
        return redirect(url_for("passwords.cambiar_password"))

    current_user.set_password(nueva)
    db.session.commit()
    session.pop("force_pwd_change", None)
    flash("Contraseña actualizada.", "success")
    return redirect(url_for("animales.lista_animales"))

# rutas para restablecer la contraseña, usuario olvido su contraseña
@bp.get("/forgot")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("animales.lista_animales"))
    return render_template("forgot_password.html")

# Enviar email con link para restablecer contraseña, usuario olvido su contraseña
@bp.post("/forgot")
def forgot_password_post():
    correo = (request.form.get("correo") or "").strip().lower()
    u = Usuario.query.filter_by(correo=correo, activo=True).first()
    if u:
        token = reset_serializer().dumps({"uid": u.usuario_id})
        reset_url = url_for("passwords.reset_password", token=token, _external=True)
        body = (
            f"Hola {u.nombre},\n\nPara restablecer tu contraseña usa este enlace "
            f"(válido por 1 hora):\n{reset_url}\n\nSi no solicitaste esto, ignora este correo."
        )
        send_email(u.correo, "Restablecer contraseña - Patitas QR", body)
    flash("Si el correo existe, te enviamos instrucciones de restablecimiento.", "success")
    return redirect(url_for("sessions.login"))

# Mostrar formulario para nueva contraseña, usuario olvido su contraseña
@bp.get("/reset/<token>")
def reset_password(token):
    try:
        data = reset_serializer().loads(token, max_age=3600)
        uid = data.get("uid")
    except SignatureExpired:
        flash("El enlace expiró. Solicita uno nuevo.", "error")
        return redirect(url_for("passwords.forgot_password"))
    except BadSignature:
        flash("Enlace inválido.", "error")
        return redirect(url_for("passwords.forgot_password"))

    u = Usuario.query.get_or_404(uid)
    return render_template("reset_password.html", token=token, correo=u.correo)

# Procesar nueva contraseña, usuario olvido su contraseña
@bp.post("/reset/<token>")
def reset_password_post(token):
    try:
        data = reset_serializer().loads(token, max_age=3600)
        uid = data.get("uid")
    except (SignatureExpired, BadSignature):
        flash("El enlace no es válido o expiró.", "error")
        return redirect(url_for("passwords.forgot_password"))

    u = Usuario.query.get_or_404(uid)
    nueva = request.form.get("nueva") or ""
    repetir = request.form.get("repetir") or ""
    if len(nueva) < 8:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("passwords.reset_password", token=token))
    if nueva != repetir:
        flash("La confirmación no coincide.", "error")
        return redirect(url_for("passwords.reset_password", token=token))

    u.set_password(nueva)
    db.session.commit()
    flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
    return redirect(url_for("sessions.login"))
