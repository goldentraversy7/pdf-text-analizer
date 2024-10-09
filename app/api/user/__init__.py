from flask import Blueprint

user_api_bp = Blueprint('user_api', __name__)

from . import routes
