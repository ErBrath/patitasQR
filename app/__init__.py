# app/__init__.py
from flask import Flask, jsonify, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
import os

from .config import get_config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())


    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "sessions.login"


    # Carpeta de uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        # Import tardío para evitar el ciclo
        from .models import Usuario
        return Usuario.query.get(int(user_id))



    @app.before_request
    def enforce_default_pwd_change():
        allow = {
            "sessions.login", "sessions.login_post", "sessions.logout",
        "sessions.bootstrap_admin", "sessions.bootstrap_admin_post",
        "passwords.cambiar_password", "passwords.cambiar_password_post",
        "passwords.forgot_password", "passwords.forgot_password_post",
        "passwords.reset_password", "passwords.reset_password_post",
        "static",
        }
        if current_user.is_authenticated and session.get("force_pwd_change"):
            if request.endpoint not in allow:
                return redirect(url_for("passwords.cambiar_password"))

    from .blueprints.animales import bp as animales_bp
    app.register_blueprint(animales_bp)

    from .blueprints.publico import bp as publico_bp
    app.register_blueprint(publico_bp)

    from .blueprints.insumos import bp as insumos_bp
    app.register_blueprint(insumos_bp)

    from .blueprints.ubicaciones import bp as ubicaciones_bp
    app.register_blueprint(ubicaciones_bp)

    from .blueprints.tratamientos import bp as tratamientos_bp
    app.register_blueprint(tratamientos_bp)

    from .blueprints.media import bp as media_bp
    app.register_blueprint(media_bp)

    from .blueprints.users import bp as users_bp
    app.register_blueprint(users_bp)

    from .blueprints.passwords import bp as passwords_bp
    app.register_blueprint(passwords_bp)

    from .blueprints.session import bp as session_bp
    app.register_blueprint(session_bp)

    @app.get("/")
    def home():
        return redirect(
            url_for("animales.lista_animales")
            if current_user.is_authenticated
            else url_for("sessions.login")
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200
    

    return app



