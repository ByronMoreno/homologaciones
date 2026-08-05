from flask import Blueprint

reports_bp = Blueprint('reports', __name__, url_prefix='/admin/reportes')

from app.reports import views
