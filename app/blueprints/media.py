from flask import Blueprint, current_app, send_from_directory, abort
import os

bp = Blueprint("media", __name__)

@bp.get("/media/<path:filename>")
def media(filename: str):
    folder = current_app.config["UPLOAD_FOLDER"]
    full = os.path.join(folder, filename)
    if not os.path.abspath(full).startswith(os.path.abspath(folder)) or not os.path.isfile(full):
        abort(404)
    return send_from_directory(folder, filename)
