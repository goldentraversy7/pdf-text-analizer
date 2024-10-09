from flask import Blueprint

user_bp = Blueprint('user', __name__, template_folder='templates', static_folder='static', static_url_path='/user/static')

from .text_routes import text_bp
from .users_routes import users_bp

user_bp.register_blueprint(users_bp)
user_bp.register_blueprint(text_bp)
