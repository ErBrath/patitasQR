from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def reset_serializer():
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"],
        salt="pwd-reset-v1"
    )
