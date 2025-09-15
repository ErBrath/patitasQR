# app/blueprints/sessions.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
from ..models import Usuario
from ..services.passwords import gen_temp_password_from_email

bp = Blueprint("sessions", __name__)

# Ruta de login
@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("animales.lista_animales"))
    return render_template("login.html")

# procesar login
@bp.post("/login")
def login_post():
    correo = (request.form.get("correo") or "").strip().lower()
    password = request.form.get("password") or ""
    u = Usuario.query.filter_by(correo=correo).first()

    if not u or not u.check_password(password):
        flash("Credenciales inválidas", "error")
        return redirect(url_for("sessions.login"))
    if not u.activo:
        flash("Tu cuenta está desactivada. Contacta a un administrador.", "error")
        return redirect(url_for("sessions.login"))

    used_temp = (password == gen_temp_password_from_email(u.correo))
    login_user(u, remember=True)
    if used_temp:
        session["force_pwd_change"] = True
        flash("Debes cambiar tu contraseña para continuar.", "warning")
        return redirect(url_for("passwords.cambiar_password"))

    session.pop("force_pwd_change", None)
    return redirect(url_for("animales.lista_animales"))

# logout
@bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("sessions.login"))

# ruta para crear el primer admin
@bp.get("/crear-admin")
def crear_admin():
    if Usuario.query.filter_by(rol="admin", activo=True).count() > 0:
        return redirect(url_for("sessions.login"))
    return render_template("crear_admin.html")

# Procesar creación del primer admin
@bp.post("/crear-admin")
def crear_admin_post():
    if Usuario.query.filter_by(rol="admin", activo=True).count() > 0:
        return redirect(url_for("sessions.login"))
    nombre = request.form.get("nombre") or ""
    apellido = request.form.get("apellido") or ""
    correo = (request.form.get("correo") or "").strip().lower()
    password = request.form.get("password") or ""
    if not (nombre and apellido and correo and password):
        abort(400, "Todos los campos son obligatorios")
    u = Usuario(nombre=nombre, apellido=apellido, correo=correo, rol="admin")
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return redirect(url_for("sessions.login"))
