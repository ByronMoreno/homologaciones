from flask import Blueprint

students_bp = Blueprint('students', __name__, url_prefix='/estudiante')

from app.students import views
