# app/blueprints/animales.py
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash, current_app
from flask_login import current_user, login_required
from .. import db
from ..models import Animal, Ubicacion, HistorialEstado, FotoAnimal, Insumo, TratamientoInsumo
from ..security import roles_required
import os, uuid
from werkzeug.utils import secure_filename


ESTADO_ANIMAL = ("En tratamiento","Recuperado","Fallecido","Observacion", "Adoptado")
bp = Blueprint("animales", __name__)

# Listar animales con búsqueda
@bp.get("/animales")
@login_required
def lista_animales():
    q = (request.args.get("q") or "").strip()
    qry = Animal.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(
            db.or_(
                Animal.nombre.ilike(like),
                Animal.especie.ilike(like),
                Animal.color.ilike(like),
            )
        )
    animales = qry.order_by(Animal.animal_id.desc()).all()
    def _key (t):
        return ((t.fecha_tratamiento or date.min), t.tratamiento_id or 0)
    ultimos = {
        a.animal_id: max(a.tratamientos, key=_key) if a.tratamientos else None
        for a in animales
    }
    
    return render_template("animals_list.html", animales=animales, q=q, ultimos=ultimos)

# ruta para formulario de nuevo animal
@bp.get("/animales/nuevo")
@login_required
def nuevo_animal():
    ubicaciones = Ubicacion.query.order_by(Ubicacion.comuna.asc(), Ubicacion.nombre_sector.asc()).all()
    return render_template("animal_new.html", ubicaciones=ubicaciones)

# Crear nuevo animal
@bp.post("/animales")
@login_required
def crear_animal():
    especie = (request.form.get("especie") or "").strip()
    if not especie:
        abort(400, "La especie es obligatoria")
    a = Animal(
        nombre=request.form.get("nombre") or None,
        especie=especie,
        sexo=request.form.get("sexo") or None,
        color=request.form.get("color") or None,
        ubicacion_id=request.form.get("ubicacion_id") or None,
        usuario_id=current_user.usuario_id,
    )
    db.session.add(a)
    db.session.commit()
    return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

# Ver detalle de animal
@bp.get("/animales/<int:animal_id>")
@login_required
def detalle_animal(animal_id:int):
    a = Animal.query.get_or_404(animal_id)
    insumos = Insumo.query.order_by(Insumo.nombre.asc()).all()
    ubicaciones = Ubicacion.query.order_by(Ubicacion.comuna.asc(), Ubicacion.nombre_sector.asc()).all()
    return render_template("animal_detail.html", animal=a, insumos=insumos, ubicaciones=ubicaciones, ESTADO_ANIMAL=ESTADO_ANIMAL)

# Formulario para editar animal
@bp.get("/animales/<int:animal_id>/editar")
@login_required
def editar_animal(animal_id:int):
    a = Animal.query.get_or_404(animal_id)
    ubicaciones = Ubicacion.query.order_by(Ubicacion.comuna.asc(), Ubicacion.nombre_sector.asc()).all()
    return render_template("animal_edit.html", animal=a, ubicaciones=ubicaciones)

# Guardar edición de animal
@bp.post("/animales/<int:animal_id>/editar")
@login_required
def guardar_edicion_animal(animal_id:int):
    a = Animal.query.get_or_404(animal_id)
    a.nombre = request.form.get("nombre") or None
    a.especie = (request.form.get("especie") or a.especie).strip() or a.especie
    a.sexo = request.form.get("sexo") or None
    a.color = request.form.get("color") or None
    a.ubicacion_id = request.form.get("ubicacion_id") or None
    db.session.commit()
    return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

# Cambiar ubicación de animal
@bp.post("/animales/<int:animal_id>/cambiar_ubicacion")
@login_required
def cambiar_ubicacion(animal_id:int):
    a = Animal.query.get_or_404(animal_id)
    a.ubicacion_id = request.form.get("ubicacion_id") or None
    db.session.commit()
    return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

# Agregar entrada al historial del animal
@bp.post("/animales/<int:animal_id>/historial")
@login_required
def agregar_historial(animal_id: int):
    a = Animal.query.get_or_404(animal_id)

    estado = (request.form.get("estado") or "").strip()
    obs    = request.form.get("observaciones") or None

    if estado not in ESTADO_ANIMAL:
        abort(400, "Estado inválido")

    pc_str = (request.form.get("proximo_control") or "").strip()
    proximo = None
    if pc_str:
        try:
            proximo = date.fromisoformat(pc_str) 
        except ValueError:
            flash("Fecha de próximo control inválida.", "error")
            return redirect(url_for("animales.historial_animal", animal_id=a.animal_id))

    h = HistorialEstado(
        animal_id=a.animal_id,
        usuario_id=current_user.usuario_id,
        estado=estado,
        observaciones=obs,
        proximo_control=proximo,   
    )

    db.session.add(h)
    db.session.commit()
    flash("Historial agregado.", "success")
    return redirect(url_for("animales.historial_animal", animal_id=a.animal_id))

# Eliminar entrada del historial del animal
@bp.post("/animales/<int:animal_id>/historial/<int:historial_id>/eliminar")
@login_required
def eliminar_historial(animal_id:int, historial_id:int):
    a = Animal.query.get_or_404(animal_id)
    h = HistorialEstado.query.get_or_404(historial_id)
    if h.animal_id != a.animal_id:
        abort(404)
    db.session.delete(h)
    db.session.commit()
    flash("Entrada de historial eliminada.", "success")
    return redirect(url_for("animales.historial_animal", animal_id=a.animal_id))

def _allowed_image(filename:str) -> bool:
    ext = filename.rsplit(".",1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]

# Subir foto de animal
@bp.post("/animales/<int:animal_id>/fotos/subir")
@login_required
def subir_foto(animal_id:int):
    a = Animal.query.get_or_404(animal_id)
    file = request.files.get("foto")
    titulo = request.form.get("titulo") or None
    if not file or file.filename == "":
        flash("Selecciona un archivo de imagen.", "error")
        return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))
    if not _allowed_image(file.filename):
        flash("Formato no permitido. Usa png, jpg, jpeg, gif o webp.", "error")
        return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

    ext = file.filename.rsplit(".",1)[-1].lower()
    subdir = f"animal/{a.animal_id}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.{ext}"
    path_abs = os.path.join(folder, secure_filename(fname))
    file.save(path_abs)

    rel = f"{subdir}/{fname}"
    f = FotoAnimal(animal_id=a.animal_id, usuario_id=current_user.usuario_id, filename=rel, titulo=titulo)
    db.session.add(f)
    db.session.commit()
    flash("Foto subida.", "success")
    return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

# Eliminar foto de animal
@bp.post("/animales/<int:animal_id>/fotos/<int:foto_id>/eliminar")
@login_required
def eliminar_foto(animal_id:int, foto_id:int):
    a = Animal.query.get_or_404(animal_id)
    f = FotoAnimal.query.get_or_404(foto_id)
    if f.animal_id != a.animal_id:
        abort(404)
    full = os.path.join(current_app.config["UPLOAD_FOLDER"], f.filename)
    try:
        if os.path.isfile(full):
            os.remove(full)
    except Exception:
        pass
    db.session.delete(f)
    db.session.commit()
    flash("Foto eliminada.", "success")
    return redirect(url_for("animales.detalle_animal", animal_id=a.animal_id))

# Ver tratamientos del animal
@bp.get("/animales/<int:animal_id>/tratamientos")
@login_required
def tratamientos_animal(animal_id: int):
    a = Animal.query.get_or_404(animal_id)
    insumos = Insumo.query.order_by(Insumo.nombre.asc()).all()
    tratamientos_ordenados = sorted(
        a.tratamientos or [],
        key=lambda t: ((t.fecha_tratamiento or date.min), t.tratamiento_id),
        reverse=True
    )

    return render_template("animal_tratamientos.html", animal=a, insumos=insumos, tratamientos=tratamientos_ordenados)

# Ver historial del animal
@bp.get("/animales/<int:animal_id>/historial")
@login_required
def historial_animal(animal_id: int):
    a = Animal.query.get_or_404(animal_id)
    return render_template("animal_historial.html", animal=a, ESTADO_ANIMAL=ESTADO_ANIMAL, today=date.today().isoformat())


# Eliminar animal y todo lo relacionado
@bp.post("/animales/<int:animal_id>/eliminar")
@roles_required("admin", "veterinario")
def eliminar_animal(animal_id: int):
    a = Animal.query.get_or_404(animal_id)

    fotos = list(a.fotos or [])
    for f in fotos:
        full = os.path.join(current_app.config["UPLOAD_FOLDER"], f.filename)
        try:
            if os.path.isfile(full):
                os.remove(full)
        except Exception:
            pass
        db.session.delete(f)

    tratamientos = list(getattr(a, "tratamientos", []) or [])
    for t in tratamientos:
        TratamientoInsumo.query.filter_by(tratamiento_id=t.tratamiento_id).delete(synchronize_session=False)
        db.session.delete(t)

    HistorialEstado.query.filter_by(animal_id=a.animal_id).delete(synchronize_session=False)

    db.session.delete(a)
    db.session.commit()

    flash("Animal eliminado junto a sus fotos, historial y tratamientos.", "success")
    return redirect(url_for("animales.lista_animales"))