# app/models.py
from . import db
from sqlalchemy import func, CheckConstraint, UniqueConstraint, Index
import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


def gen_uuid():
    """Genera un UUID en str para usar como token público (QR)."""
    return str(uuid.uuid4())



class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"

    usuario_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(50), unique=True, nullable=False)
    hash_contrasena = db.Column(db.String(255), nullable=False) 
    rol = db.Column(db.String(20), nullable=False, default="asistente")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, server_default=func.current_timestamp())

    __table_args__ = (
        CheckConstraint(
            "rol IN ('admin','veterinario','asistente')",
            name="usuario_rol_chk",
        ),
        UniqueConstraint("correo", name="usuario_correo_uk"),
        Index("ix_usuario_correo", "correo"),
    )
    def get_id(self) -> str:
        return str(self.usuario_id)

    def set_password(self, raw: str) -> None:
        self.hash_contrasena = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.hash_contrasena, raw)

    def __repr__(self):
        return f"<Usuario {self.usuario_id} {self.correo} ({self.rol})>"



class Ubicacion(db.Model):
    __tablename__ = "ubicacion"

    ubicacion_id = db.Column(db.Integer, primary_key=True)
    comuna = db.Column(db.String(50), nullable=False)
    nombre_sector = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=func.current_timestamp())

    def __repr__(self):
        return f"<Ubicacion {self.ubicacion_id} {self.comuna}-{self.nombre_sector}>"


class Animal(db.Model):
    __tablename__ = "animal"

    animal_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    especie = db.Column(db.String(50), nullable=False)       
    sexo = db.Column(db.String(10))                           
    color = db.Column(db.String(50))
    codigo_qr = db.Column(db.String(255), unique=True, nullable=False, default=gen_uuid)
    fecha_registro = db.Column(db.Date, nullable=False, server_default=func.current_date())


    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.usuario_id", ondelete="SET NULL"),
        nullable=True,
    )
    ubicacion_id = db.Column(
        db.Integer,
        db.ForeignKey("ubicacion.ubicacion_id", ondelete="SET NULL"),
        nullable=True,
    )
    historial_estados = db.relationship(
        "HistorialEstado",
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="desc(HistorialEstado.fecha_estado)",
    )
    fotos = db.relationship(
        "FotoAnimal",
        back_populates="animal",
        cascade="all, delete-orphan",
        order_by="desc(FotoAnimal.fecha_subida)",
    )

    usuario = db.relationship("Usuario", backref="animales")
    ubicacion = db.relationship("Ubicacion", backref="animales")

    __table_args__ = (
        CheckConstraint(
            "sexo IN ('Macho','Hembra') OR sexo IS NULL",
            name="animal_sexo_chk",
        ),
        UniqueConstraint("codigo_qr", name="animal_codigo_qr_uk"),
        Index("ix_animal_ubicacion", "ubicacion_id"),
    )

    def __repr__(self):
        return f"<Animal {self.animal_id} {self.especie} qr={self.codigo_qr}>"


class Tratamiento(db.Model):
    __tablename__ = "tratamiento"

    tratamiento_id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)           
    descripcion = db.Column(db.String(250))
    fecha_tratamiento = db.Column(db.Date, nullable=False, server_default=func.current_date())
    estado = db.Column(db.String(50), nullable=False, default="Pendiente") 

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.usuario_id", ondelete="RESTRICT"),
        nullable=False,
    )
    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animal.animal_id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario = db.relationship("Usuario", backref="tratamientos")
    animal = db.relationship("Animal", backref="tratamientos")

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente','Aprobado','Rechazado')",
            name="tratamiento_estado_chk",
        ),
        Index("ix_tratamiento_animal_fecha", "animal_id", "fecha_tratamiento"),
    )

    def __repr__(self):
        return f"<Tratamiento {self.tratamiento_id} {self.tipo} {self.estado}>"


class Insumo(db.Model):
    __tablename__ = "insumo"

    insumo_id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    unidad = db.Column(db.String(50), nullable=False)        
    stock = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    fecha_vencimiento = db.Column(db.Date)

    __table_args__ = (
        CheckConstraint("stock >= 0", name="insumo_stock_chk"),
    )

    def __repr__(self):
        return f"<Insumo {self.insumo_id} {self.nombre} stock={self.stock}>"


class TratamientoInsumo(db.Model):
    __tablename__ = "tratamiento_insumo"

    tratamiento_id = db.Column(
        db.Integer,
        db.ForeignKey("tratamiento.tratamiento_id", ondelete="CASCADE"),
        primary_key=True,
    )
    insumo_id = db.Column(
        db.Integer,
        db.ForeignKey("insumo.insumo_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    cantidad = db.Column(db.Numeric(10, 2), nullable=False)  # > 0

    tratamiento = db.relationship("Tratamiento", backref="detalle_insumos")
    insumo = db.relationship("Insumo")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="tratamiento_insumo_cantidad_chk"),
        Index("ix_tratinsumo_insumo", "insumo_id"),
    )

    def __repr__(self):
        return f"<TratamientoInsumo t={self.tratamiento_id} i={self.insumo_id} cant={self.cantidad}>"



class HistorialEstado(db.Model):
    __tablename__ = "historial_estado"
    historial_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animal.animal_id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.usuario_id", ondelete="SET NULL"))
    estado = db.Column(db.String(30), nullable=False) 
    observaciones = db.Column(db.Text)
    fecha_estado = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    proximo_control = db.Column(db.Date, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "estado in ('En tratamiento','Recuperado','Adoptado','Fallecido','Observacion')",
            name="historial_estado_chk",
        ),
    )

    animal = db.relationship("Animal", back_populates="historial_estados")
    usuario = db.relationship("Usuario")

class FotoAnimal(db.Model):
    __tablename__ = "foto_animal"
    foto_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animal.animal_id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.usuario_id", ondelete="SET NULL"))
    filename = db.Column(db.String(255), nullable=False) 
    titulo = db.Column(db.String(100))
    fecha_subida = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    animal = db.relationship("Animal", back_populates="fotos")
    usuario = db.relationship("Usuario")