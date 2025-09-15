# app/blueprints/ubicaciones.py
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Ubicacion, Animal
from ..security import roles_required

bp = Blueprint("ubicaciones", __name__)

# Lista de ubicaciones
@bp.get("/ubicaciones")
@login_required
def lista_ubicaciones():
    q = (request.args.get("q") or "").strip()
    qry = Ubicacion.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(Ubicacion.comuna.ilike(like),
                             Ubicacion.nombre_sector.ilike(like),
                             Ubicacion.descripcion.ilike(like)))
    ubicaciones = qry.order_by(Ubicacion.comuna.asc(), Ubicacion.nombre_sector.asc()).all()
    return render_template("ubicaciones_list.html", ubicaciones=ubicaciones, q=q)

# Crear nueva ubicacion
@bp.post("/ubicaciones")
@roles_required("veterinario", "asistente", "admin")
def crear_ubicacion():
    comuna = (request.form.get("comuna") or "").strip()
    sector = (request.form.get("nombre_sector") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()
    if not (comuna and sector):
        abort(400, "comuna y nombre_sector son obligatorios")

    existente = (Ubicacion.query
                 .filter(
                     func.lower(Ubicacion.comuna) == comuna.lower(),
                     func.lower(Ubicacion.nombre_sector) == sector.lower(),
                     func.lower(func.coalesce(Ubicacion.descripcion, "")) == descripcion.lower()
                 )
                 .first())
    if existente:
        flash("Ya existe una ubicación con esa comuna, sector y descripción.", "error")
        return redirect(url_for("ubicaciones.lista_ubicaciones"))

    u = Ubicacion(comuna=comuna, nombre_sector=sector, descripcion=(descripcion or None))
    db.session.add(u)
    try:
        db.session.commit()
        flash("Ubicación creada.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo crear la ubicación.", "error")
    return redirect(url_for("ubicaciones.lista_ubicaciones"))

# Ruta edita ubicacion
@bp.get("/ubicaciones/<int:ubicacion_id>/editar")
@roles_required("veterinario", "asistente", "admin")
def editar_ubicacion(ubicacion_id: int):
    u = Ubicacion.query.get_or_404(ubicacion_id)
    return render_template("ubicacion_edit.html", ubicacion=u)

# Procesar edicion de ubicacion
@bp.post("/ubicaciones/<int:ubicacion_id>/editar")
@roles_required("veterinario", "asistente", "admin")
def guardar_edicion_ubicacion(ubicacion_id: int):
    u = Ubicacion.query.get_or_404(ubicacion_id)
    comuna = (request.form.get("comuna") or "").strip()
    sector = (request.form.get("nombre_sector") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()
    if not (comuna and sector):
        abort(400, "comuna y nombre_sector son obligatorios")

    existente = (Ubicacion.query
                 .filter(
                     func.lower(Ubicacion.comuna) == comuna.lower(),
                     func.lower(Ubicacion.nombre_sector) == sector.lower(),
                     func.lower(func.coalesce(Ubicacion.descripcion, "")) == descripcion.lower(),
                     Ubicacion.ubicacion_id != u.ubicacion_id
                 )
                 .first())
    if existente:
        flash("Ya existe otra ubicación con la misma comuna, sector y descripción.", "error")
        return redirect(url_for("ubicaciones.editar_ubicacion", ubicacion_id=u.ubicacion_id))

    u.comuna = comuna
    u.nombre_sector = sector
    u.descripcion = (descripcion or None)
    try:
        db.session.commit()
        flash("Ubicación actualizada.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo actualizar la ubicación.", "error")
    return redirect(url_for("ubicaciones.lista_ubicaciones"))

# Eliminar ubicacion
@bp.post("/ubicaciones/<int:ubicacion_id>/eliminar")
@roles_required("veterinario", "asistente", "admin")
def eliminar_ubicacion(ubicacion_id: int):
    u = Ubicacion.query.get_or_404(ubicacion_id)

    en_uso = (Animal.query.filter_by(ubicacion_id=ubicacion_id)
              .limit(1).first())
    if en_uso:
        flash("No se puede eliminar: hay animales asociados a esta ubicación.", "error")
        return redirect(url_for("ubicaciones.lista_ubicaciones"))

    try:
        db.session.delete(u)
        db.session.commit()
        flash("Ubicación eliminada.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo eliminar por restricciones de integridad.", "error")
    return redirect(url_for("ubicaciones.lista_ubicaciones"))
