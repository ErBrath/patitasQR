# app/blueprints/insumos.py
from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Insumo, TratamientoInsumo

bp = Blueprint("insumos", __name__)

# Listar insumos con búsqueda
@bp.get("/insumos")
@login_required
def lista_insumos():
    q = (request.args.get("q") or "").strip()
    qry = Insumo.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(
            db.or_(
                Insumo.nombre.ilike(like),
                Insumo.unidad.ilike(like),
            )
        )
    insumos = qry.order_by(Insumo.nombre.asc()).all()
    return render_template("insumos_list.html", insumos=insumos, q=q, today=date.today().isoformat())

# Crear nuevo insumo
@bp.post("/insumos")
@login_required
def crear_insumo():
    nombre_raw = (request.form.get("nombre") or "").strip()
    unidad_raw = (request.form.get("unidad") or "").strip()
    stock_val  = request.form.get("stock", type=float, default=0.0)
    fv_raw     = request.form.get("fecha_vencimiento") or ""


    if not (nombre_raw and unidad_raw):
        abort(400, "nombre y unidad son obligatorios")

    nombre = " ".join(nombre_raw.split())
    unidad = " ".join(unidad_raw.split())
    try:
        stock = Decimal(str(stock_val))
        if stock < 0:
            stock = Decimal("0")
    except Exception:
        stock = Decimal("0")
    
    fv = None
    fv_raw = request.form.get("fecha_vencimiento") or ""
    if fv_raw:
        try:
            fv = datetime.strptime(fv_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Fecha de vencimiento inválida. Use AAAA-MM-DD.", "error")
            return redirect(url_for("insumos.lista_insumos"))
    
    if fv and fv < date.today():
        flash("No se puede registrar un insumo con fecha de vencimiento pasada.", "error")
        return redirect(url_for("insumos.lista_insumos"))

    
    existente = Insumo.query.filter(func.lower(Insumo.nombre) == nombre.lower()).first()
    if existente:
        if existente.fecha_vencimiento and existente.fecha_vencimiento < date.today():
            flash(
            f"El insumo “{existente.nombre}” está vencido (vence: {existente.fecha_vencimiento}). "
            "Actualiza la fecha de vencimiento antes de sumar stock.",
            "error",
        )

        
        if existente.unidad.lower() == unidad.lower():

            if fv and fv < date.today():
                flash("No se puede registrar stock con fecha de vencimiento pasada.", "error")
                return redirect(url_for("insumos.lista_insumos"))

            existente.stock = (existente.stock or Decimal("0")) + stock
            if fv and (existente.fecha_vencimiento is None or fv > existente.fecha_vencimiento):
                existente.fecha_vencimiento = fv  # opcional: mantener la más lejana
            try:
                db.session.commit()
                flash(f"El insumo “{existente.nombre}” ya existía: se sumó {stock} {unidad} al stock.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("No se pudo actualizar el stock por un error de integridad.", "error")
            return redirect(url_for("insumos.lista_insumos"))
        else:
            flash(
                f"Ya existe un insumo llamado “{existente.nombre}” con unidad “{existente.unidad}”. "
                "Cámbiale el nombre o la unidad para crearlo aparte.",
                "error",
            )
            return redirect(url_for("insumos.lista_insumos"))

    i = Insumo(nombre=nombre, unidad=unidad, stock=stock, fecha_vencimiento=fv)
    db.session.add(i)
    try:
        db.session.commit()
        flash("Insumo creado.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un insumo con ese nombre.", "error")
    return redirect(url_for("insumos.lista_insumos"))

# Ajustar stock (agregar o quitar)
@bp.post("/insumos/<int:insumo_id>/ajustar")
@login_required
def ajustar_stock(insumo_id: int):
    delta_val = request.form.get("delta", type=float)
    if delta_val is None:
        abort(400, "delta requerido")
    i = Insumo.query.get_or_404(insumo_id)
    nuevo = (i.stock or Decimal("0")) + Decimal(str(delta_val))
    if nuevo < 0:
        flash("El stock no puede quedar negativo.", "error")
        return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))
    i.stock = nuevo
    db.session.commit()
    flash("Stock actualizado.", "success")
    return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))

# Formulario para editar insumo
@bp.get("/insumos/<int:insumo_id>/editar")
@login_required
def editar_insumo(insumo_id: int):
    i = Insumo.query.get_or_404(insumo_id)
    return render_template("insumo_edit.html", insumo=i, today=date.today().isoformat())

# Guardar edición de insumo (excepto stock)
@bp.post("/insumos/<int:insumo_id>/editar")
@login_required
def guardar_edicion_insumo(insumo_id: int):
    i = Insumo.query.get_or_404(insumo_id)
    nombre_raw = (request.form.get("nombre") or "").strip()
    unidad_raw = (request.form.get("unidad") or "").strip()
    fv_raw     = request.form.get("fecha_vencimiento") or ""

    if not (nombre_raw and unidad_raw):
        abort(400, "nombre y unidad son obligatorios")

    nombre = " ".join(nombre_raw.split())
    unidad = " ".join(unidad_raw.split())

    existente = (
        Insumo.query
        .filter(func.lower(Insumo.nombre) == nombre.lower(), Insumo.insumo_id != i.insumo_id)
        .first()
    )
    if existente:
        flash(f"Ya existe otro insumo llamado “{existente.nombre}”. Cambia el nombre.", "error")
        return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))

    i.nombre = nombre
    i.unidad = unidad

    if fv_raw:
        try:
            nueva_fv = datetime.strptime(fv_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Fecha de vencimiento inválida. Use AAAA-MM-DD.", "error")
            return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))

        if nueva_fv < date.today():
            flash("No puedes establecer una fecha de vencimiento pasada.", "error")
            return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))

        i.fecha_vencimiento = nueva_fv
    else:
        i.fecha_vencimiento = None

    try:
        db.session.commit()
        flash("Datos de Insumo actualizado. El stock se ajusta por separado.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo actualizar (posible duplicado).", "error")
    return redirect(url_for("insumos.editar_insumo", insumo_id=i.insumo_id))

# Eliminar insumo (si no está en uso)
@bp.post("/insumos/<int:insumo_id>/eliminar")
@login_required
def eliminar_insumo(insumo_id: int):
    i = Insumo.query.get_or_404(insumo_id)
    en_uso = db.session.query(TratamientoInsumo).filter_by(insumo_id=insumo_id).limit(1).first()
    if en_uso:
        flash("No se puede eliminar: el insumo está siendo usado en tratamientos.", "error")
        return redirect(url_for("insumos.lista_insumos"))

    try:
        db.session.delete(i)
        db.session.commit()
        flash("Insumo eliminado.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo eliminar por restricciones de integridad.", "error")
    return redirect(url_for("insumos.lista_insumos"))


