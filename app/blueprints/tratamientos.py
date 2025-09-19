# app/blueprints/tratamientos.py
from flask import Blueprint, request, redirect, url_for, abort, flash, render_template
from sqlalchemy.exc import IntegrityError
from flask_login import current_user
from .. import db
from ..models import Tratamiento, TratamientoInsumo, Insumo
from ..security import roles_required
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import date

bp = Blueprint("tratamientos", __name__)

# crear tratamiento
@bp.post("/tratamientos")
@roles_required("veterinario", "asistente", "admin")
def crear_tratamiento():
    animal_id = request.form.get("animal_id", type=int)
    tipo = (request.form.get("tipo") or "").strip()
    descripcion = request.form.get("descripcion") or None

    if not (animal_id and tipo):
        abort(400, "animal_id y tipo son obligatorios")

    t = Tratamiento(
        animal_id=animal_id,
        tipo=tipo,
        descripcion=descripcion,
        usuario_id=current_user.usuario_id
    )
    t.estado = "Pendiente"
    db.session.add(t)

    insumo_ids = request.form.getlist("insumo_id[]") or request.form.getlist("insumo_id")
    cantidades = request.form.getlist("cantidad[]") or request.form.getlist("cantidad")

    totales = {}
    for sid, sc in zip(insumo_ids, cantidades):
      if not sid or not sc:
          continue
      try:
          ins_id = int(sid)
          q = Decimal(str(sc))
      except Exception:
          continue
      if q <= 0:
          continue
      totales[ins_id] = totales.get(ins_id, Decimal("0")) + q

    for ins_id, q in totales.items():
        db.session.add(TratamientoInsumo(tratamiento=t, insumo_id=ins_id, cantidad=q))

    if totales:
        faltantes = []
        for ins_id, req in totales.items():
            i = Insumo.query.get(ins_id)
            if i and i.stock is not None and i.stock < req:
                faltantes.append(f"{i.nombre} (disp: {i.stock}, req: {req})")
        if faltantes:
            flash("Algunas cantidades superan el stock actual: " + "; ".join(faltantes) +
                  ". Se guardó Pendiente; ajusta cantidades o repón stock antes de aprobar.", "warning")

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Error de integridad al crear tratamiento")

    return redirect(url_for("animales.tratamientos_animal", animal_id=animal_id))


# Aprobar tratamiento (y descontar stock)
@bp.post("/tratamientos/<int:tratamiento_id>/aprobar")
@roles_required("veterinario", "admin")
def aprobar_tratamiento(tratamiento_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        flash("Solo se puede aprobar un tratamiento en estado Pendiente.", "error")
        return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))

    detalles = list(t.detalle_insumos or [])
    if not detalles:
        t.estado = "Aprobado"
        db.session.commit()
        flash("Tratamiento aprobado (sin insumos).", "success")
        return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))

    faltantes = []
    for d in detalles:
        i = Insumo.query.get(d.insumo_id)
        if not i:
            faltantes.append(f"Insumo #{d.insumo_id} inexistente")
            continue
        disp = i.stock or Decimal("0")
        req = d.cantidad
        if disp < req:
            faltantes.append(f"{i.nombre} (disponible: {disp}, requerido: {req})")
        if i.fecha_vencimiento and i.fecha_vencimiento < date.today():
            faltantes.append(f"{i.nombre} vencido (vence: {i.fecha_vencimiento})")

    if faltantes:
        flash("No se pudo aprobar por falta de: " + "; ".join(faltantes), "error")
        return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))

    try:
        ids = [d.insumo_id for d in detalles]
        locked_insumos = (
            db.session.execute(
                select(Insumo)
                .where(Insumo.insumo_id.in_(ids))
                .with_for_update()
            ).scalars().all()
        )
        locked_map = {i.insumo_id: i for i in locked_insumos}

        for d in detalles:
            i = locked_map.get(d.insumo_id)
            if not i:
                db.session.rollback()
                flash(f"Insumo #{d.insumo_id} inexistente.", "error")
                return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))
            disp = i.stock or Decimal("0")
            req = d.cantidad
            if disp < req:
                db.session.rollback()
                flash(f"Stock insuficiente de {i.nombre}. Disp: {disp}, req: {req}", "error")
                return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))
            if i.fecha_vencimiento and i.fecha_vencimiento < date.today():
                db.session.rollback()
                flash(f"El insumo {i.nombre} está vencido (vence: {i.fecha_vencimiento}).", "error")
                return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))

        for d in detalles:
            i = locked_map[d.insumo_id]
            i.stock = (i.stock or Decimal("0")) - d.cantidad

        t.estado = "Aprobado"
        db.session.add(t)
        db.session.commit()
        flash("Tratamiento aprobado y stock actualizado ✅", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Ocurrió un error al aprobar el tratamiento.", "error")

    return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))


# Rechazar tratamiento
@bp.post("/tratamientos/<int:tratamiento_id>/rechazar")
@roles_required("veterinario", "admin")
def rechazar_tratamiento(tratamiento_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        abort(400, "Solo se puede rechazar un tratamiento Pendiente")
    t.estado = "Rechazado"
    db.session.commit()
    return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))


# Actualizar cantidad en línea de detalle
@bp.post("/tratamientos/<int:tratamiento_id>/detalle/<int:insumo_id>/actualizar")
@roles_required("veterinario", "asistente", "admin")
def actualizar_cantidad_detalle(tratamiento_id: int, insumo_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        abort(400, "Solo se puede editar un tratamiento Pendiente")

    d = TratamientoInsumo.query.get((tratamiento_id, insumo_id))
    if not d:
        abort(404, "Detalle no encontrado")

    nueva_cant = request.form.get("cantidad", type=float)
    if nueva_cant is None or nueva_cant <= 0:
        abort(400, "La cantidad debe ser > 0")

    d.cantidad = Decimal(str(nueva_cant))
    db.session.commit()
    return redirect(url_for("tratamientos.tratamiento_edit", tratamiento_id=t.tratamiento_id))


# Agregar línea de insumo
@bp.post("/tratamientos/<int:tratamiento_id>/detalle/agregar")
@roles_required("veterinario", "asistente", "admin")
def agregar_linea_detalle(tratamiento_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        abort(400, "Solo se puede editar un tratamiento Pendiente")

    insumo_id = request.form.get("insumo_id", type=int)
    cantidad  = request.form.get("cantidad", type=float)
    if not (insumo_id and cantidad is not None):
        abort(400, "Insumo y cantidad son obligatorios")
    if cantidad <= 0:
        abort(400, "La cantidad debe ser > 0")

    q = Decimal(str(cantidad))
    d = TratamientoInsumo.query.get((tratamiento_id, insumo_id))
    if d:
        d.cantidad = d.cantidad + q
    else:
        d = TratamientoInsumo(tratamiento_id=tratamiento_id, insumo_id=insumo_id, cantidad=q)
        db.session.add(d)

    i = Insumo.query.get(insumo_id)
    if i and i.stock is not None and i.stock < d.cantidad:
        flash(f"La cantidad total de {i.nombre} (req: {d.cantidad}) supera stock actual ({i.stock}). "
              "Podrás aprobar cuando repongas stock o reduzcas la cantidad.", "warning")

    db.session.commit()
    return redirect(url_for("tratamientos.tratamiento_edit", tratamiento_id=t.tratamiento_id))


# Eliminar una línea de insumo
@bp.post("/tratamientos/<int:tratamiento_id>/detalle/<int:insumo_id>/eliminar")
@roles_required("veterinario", "asistente", "admin")
def eliminar_linea_detalle(tratamiento_id: int, insumo_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        abort(400, "Solo se puede editar un tratamiento Pendiente")

    d = TratamientoInsumo.query.get((tratamiento_id, insumo_id))
    if not d:
        abort(404, "Detalle no encontrado")

    db.session.delete(d)
    db.session.commit()
    flash("Línea eliminada.", "success")
    return redirect(url_for("animales.tratamientos_animal", animal_id=t.animal_id))

# Ruta editar insumo
@bp.get("/tratamientos/<int:tratamiento_id>")
@roles_required("veterinario", "asistente", "admin")
def tratamiento_edit(tratamiento_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    insumos = Insumo.query.order_by(Insumo.nombre.asc()).all()
    return render_template("tratamiento_edit.html", t=t, insumos=insumos)

# Actualizar tratamiento
@bp.post("/tratamientos/<int:tratamiento_id>/actualizar")
@roles_required("veterinario", "asistente", "admin")
def actualizar_tratamiento(tratamiento_id: int):
    t = Tratamiento.query.get_or_404(tratamiento_id)
    if t.estado != "Pendiente":
        flash("Solo se puede editar un tratamiento en estado Pendiente.", "error")
        return redirect(url_for("tratamientos.tratamiento_edit", tratamiento_id=tratamiento_id))

    tipo = (request.form.get("tipo") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip() or None
    if not tipo:
        flash("El tipo es obligatorio.", "error")
        return redirect(url_for("tratamientos.tratamiento_edit", tratamiento_id=tratamiento_id))

    t.tipo = tipo
    t.descripcion = descripcion
    try:
        db.session.commit()
        flash("Cambios guardados.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo guardar el tratamiento.", "error")

    return redirect(url_for("tratamientos.tratamiento_edit", tratamiento_id=tratamiento_id))
