from flask import Flask,jsonify
import datetime

from .api.user import user_api_bp
from .user import user_bp
from .mongo import get_db
from .extension import jwt
from .config import Config

import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = os.getenv('APP_SECRET_KEY')

    jwt.init_app(app)
    
    # Register blueprints
    app.register_blueprint(user_api_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/')

    app.teardown_appcontext(lambda ctx: get_db().client.close())

    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=8)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_headers, jwt_data):
        identity = jwt_data['sub']
        return identity

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({"message", "token has expired"}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"message", "Signature verification failed"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"message", "token has expired"}), 401


    return app
