# app/blueprints/users.py
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Usuario, Tratamiento, HistorialEstado, FotoAnimal, Animal
from ..security import roles_required
from ..services.mail import send_email
from ..services.passwords import gen_temp_password_from_email

bp = Blueprint("users", __name__)

def _admins_activos_count():
    return Usuario.query.filter_by(rol="admin", activo=True).count()

def _vets_activos_count():
    return Usuario.query.filter_by(rol="veterinario", activo=True).count()

# lista de usuarios
@bp.get("/usuarios")
@roles_required("admin", "veterinario")
def usuarios_list():
    q = (request.args.get("q") or "").strip()
    qry = Usuario.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(Usuario.nombre.ilike(like),
                             Usuario.apellido.ilike(like),
                             Usuario.correo.ilike(like)))
    usuarios = qry.order_by(Usuario.activo.desc(), Usuario.rol.asc(),
                            Usuario.apellido.asc(), Usuario.nombre.asc()).all()
    return render_template("usuarios_list.html", usuarios=usuarios, q=q)

# Ruta para crear nuevo usuario
@bp.get("/usuarios/nuevo")
@roles_required("admin", "veterinario")
def usuarios_nuevo():
    return render_template("usuarios_new.html")

# Crear nuevo usuario
@bp.post("/usuarios")
@roles_required("admin", "veterinario")
def usuarios_crear():
    nombre = (request.form.get("nombre") or "").strip()
    apellido = (request.form.get("apellido") or "").strip()
    correo = (request.form.get("correo") or "").strip().lower()
    rol_req = (request.form.get("rol") or "asistente").strip()

    if current_user.rol == "admin":
        if rol_req not in ("veterinario", "asistente"):
            abort(400, "Rol inválido")
        rol_final = rol_req
    else:
        rol_final = "asistente"

    if not (nombre and apellido and correo):
        abort(400, "Campos obligatorios faltantes")

    temp_pwd = gen_temp_password_from_email(correo)
    u = Usuario(nombre=nombre, apellido=apellido, correo=correo, rol=rol_final)
    u.set_password(temp_pwd)
    db.session.add(u)
    try:
        db.session.commit()
        login_url = url_for("sessions.login", _external=True)
        body = (
            f"Hola {u.nombre},\n\nTu cuenta en Patitas QR fue creada.\n"
            f"Correo: {u.correo}\nContraseña temporal: {temp_pwd}\n\n"
            f"Ingresa aquí: {login_url}\n"
            f"Al iniciar sesión con la clave temporal, se te pedirá cambiarla.\n\n"
            f"Si no solicitaste esta cuenta, ignora este mensaje."
        )
        send_email(u.correo, "Acceso a Patitas QR", body)
        flash("Usuario creado. Se envió una contraseña temporal al correo.", "success")
    except IntegrityError as e:
        db.session.rollback()
        pgcode = getattr(getattr(e, "orig", None), "pgcode", None)
        if pgcode == "23505":
            flash("Ya existe un usuario con ese correo.", "error")
        elif pgcode == "23514":
            flash("Rol inválido.", "error")
        else:
            flash("No se pudo crear el usuario.", "error")

    return redirect(url_for("users.usuarios_list"))

# Cambiar rol a un usuario
@bp.post("/usuarios/<int:usuario_id>/rol")
@roles_required("admin")
def usuario_cambiar_rol(usuario_id:int):
    u = Usuario.query.get_or_404(usuario_id)
    nuevo = (request.form.get("rol") or "").strip()
    if nuevo not in ("admin", "veterinario", "asistente"):
        abort(400, "Rol inválido")

    if u.usuario_id == current_user.usuario_id and u.rol == "admin" and nuevo != "admin":
        flash("No puedes cambiar tu propio rol (perderías privilegios de admin).", "error")
        return redirect(url_for("users.usuarios_list"))

    if u.rol == "admin" and nuevo != "admin" and _admins_activos_count() <= 1:
        flash("No puedes cambiar el rol del único admin activo.", "error")
        return redirect(url_for("users.usuarios_list"))

    if u.rol == "veterinario" and nuevo != "veterinario" and _vets_activos_count() <= 1:
        flash("No puedes cambiar el rol del único veterinario activo.", "error")
        return redirect(url_for("users.usuarios_list"))

    u.rol = nuevo
    db.session.commit()
    flash("Rol actualizado.", "success")
    return redirect(url_for("users.usuarios_list"))

# Desactivar usuario
@bp.post("/usuarios/<int:usuario_id>/desactivar")
@roles_required("admin")
def usuario_desactivar(usuario_id:int):
    u = Usuario.query.get_or_404(usuario_id)
    if u.usuario_id == current_user.usuario_id:
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("users.usuarios_list"))
    if u.rol == "admin" and u.activo and _admins_activos_count() <= 1:
        flash("No puedes desactivar al único admin activo.", "error")
        return redirect(url_for("users.usuarios_list"))
    if u.rol == "veterinario" and u.activo and _vets_activos_count() <= 1:
        flash("No puedes desactivar al único veterinario activo.", "error")
        return redirect(url_for("users.usuarios_list"))
    u.activo = False
    db.session.commit()
    flash("Usuario desactivado.", "success")
    return redirect(url_for("users.usuarios_list"))

# Activar usuario
@bp.post("/usuarios/<int:usuario_id>/activar")
@roles_required("admin")
def usuario_activar(usuario_id:int):
    u = Usuario.query.get_or_404(usuario_id)
    u.activo = True
    db.session.commit()
    flash("Usuario activado.", "success")
    return redirect(url_for("users.usuarios_list"))

# Eliminar usuario
@bp.post("/usuarios/<int:usuario_id>/eliminar")
@roles_required("admin")
def usuario_eliminar(usuario_id:int):
    u = Usuario.query.get_or_404(usuario_id)
    if u.usuario_id == current_user.usuario_id:
        flash("No puedes eliminar tu propia cuenta.", "error")
        return redirect(url_for("users.usuarios_list"))
    if u.rol == "admin" and u.activo and _admins_activos_count() <= 1:
        flash("No puedes eliminar al único admin activo.", "error")
        return redirect(url_for("users.usuarios_list"))
    if u.rol == "veterinario" and u.activo and _vets_activos_count() <= 1:
        flash("No puedes eliminar al único veterinario activo.", "error")
        return redirect(url_for("users.usuarios_list"))

    if (db.session.query(Tratamiento).filter_by(usuario_id=usuario_id).first()
        or db.session.query(HistorialEstado).filter_by(usuario_id=usuario_id).first()
        or db.session.query(FotoAnimal).filter_by(usuario_id=usuario_id).first()
        or db.session.query(Animal).filter_by(usuario_id=usuario_id).first()
    ):
        flash("No se puede eliminar: tiene registros asociados. Desactívalo.", "error")
        return redirect(url_for("users.usuarios_list"))

    db.session.delete(u)
    db.session.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for("users.usuarios_list"))
