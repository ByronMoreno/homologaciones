import os
from flask import Flask, redirect, url_for
from config import config_by_name
from extensions import db, migrate, login_manager, jwt, mail, limiter, cache

def create_app(config_name='default') -> Flask:
    """Factory Pattern para crear e inicializar la aplicación Flask."""
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config_by_name[config_name])
    
    # Asegurar que exista la carpeta de subidas de archivos
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Registrar modelos en la metadata de SQLAlchemy para migraciones
    from app import models
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'
    
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    
    # Registrar Blueprints
    from app.auth import auth_bp
    from app.homologaciones import homologaciones_bp
    from app.students import students_bp
    from app.faq import faq_bp
    from app.reports import reports_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(homologaciones_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(faq_bp)
    app.register_blueprint(reports_bp)
    
    # Redirección de la raíz al login del estudiante
    @app.route('/')
    def index():
        return redirect(url_for('students.login'))
    
    # Context Processor para la shell de flask
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Usuario, Rol, Carrera, Estudiante, Solicitud, Documento, TipoDocumento, Seguimiento, Observacion, FAQ, FAQCategoria
        return {
            'db': db,
            'Usuario': Usuario,
            'Rol': Rol,
            'Carrera': Carrera,
            'Estudiante': Estudiante,
            'Solicitud': Solicitud,
            'Documento': Documento,
            'TipoDocumento': TipoDocumento,
            'Seguimiento': Seguimiento,
            'Observacion': Observacion,
            'FAQ': FAQ,
            'FAQCategoria': FAQCategoria
        }
        
    # Registrar comandos CLI
    from app.commands import seed_db
    app.cli.add_command(seed_db)
        
    return app
