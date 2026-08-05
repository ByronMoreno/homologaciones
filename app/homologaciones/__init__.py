from flask import Blueprint

homologaciones_bp = Blueprint('homologaciones', __name__, url_prefix='/admin')

from app.homologaciones import views
