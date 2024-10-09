
from flask_jwt_extended import JWTManager
from itsdangerous import URLSafeTimedSerializer

import os
from dotenv import load_dotenv

load_dotenv()

jwt = JWTManager()

s = URLSafeTimedSerializer(os.getenv('APP_SECRET_KEY'))