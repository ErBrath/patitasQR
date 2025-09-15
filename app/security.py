from functools import wraps
from flask_login import login_required, current_user
from flask import abort

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.rol not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco

