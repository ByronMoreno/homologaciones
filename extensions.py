from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()

# Inicializamos el limitador con una función de clave por defecto, sin asociarlo a ninguna app aún
limiter = Limiter(key_func=get_remote_address, default_limits=["5000 per day", "1000 per hour"])
cache = Cache()
