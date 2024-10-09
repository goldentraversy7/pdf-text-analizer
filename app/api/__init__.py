from flask import Blueprint

# Create blueprints for API
admin_api_bp = Blueprint('admin_api', __name__)
user_api_bp = Blueprint('user_api', __name__)

# Import routes after creating blueprints to avoid circular imports
# from .admin import routes as admin_routes
from .user import routes as user_routes
