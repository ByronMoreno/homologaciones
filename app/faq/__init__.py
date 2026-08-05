from flask import Blueprint

faq_bp = Blueprint('faq', __name__, url_prefix='/faq')

from app.faq import views
