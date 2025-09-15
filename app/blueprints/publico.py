# app/blueprints/publico.py
from flask import Blueprint, current_app, render_template, send_file, abort
from ..models import Animal, Tratamiento
import qrcode, io

bp = Blueprint("publico", __name__)

# Ruta para mostrar la ficha pública del animal
@bp.get("/p/<token>")
def ficha_publica(token: str):
    animal = Animal.query.filter_by(codigo_qr=token).first()
    if not animal:
        abort(404)
    tratamientos_aprobados = (
        Tratamiento.query
        .filter_by(animal_id=animal.animal_id, estado="Aprobado")
        .order_by(Tratamiento.fecha_tratamiento.desc())
        .limit(5)
        .all()
    )
    return render_template("public_animal.html", animal=animal, tratamientos=tratamientos_aprobados)

# Ruta para generar y servir el código QR como imagen PNG
@bp.get("/qr/<token>.png")
def qr_png(token: str):
    base = current_app.config.get("QR_PUBLIC_BASE_URL", "http://localhost:5000")
    url = f"{base}/p/{token}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

