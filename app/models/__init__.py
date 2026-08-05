from datetime import datetime
from typing import List, Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager

class Rol(db.Model):
    """Modelo para roles de usuario en el sistema."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

    def __repr__(self) -> str:
        return f"<Rol {self.name}>"


class Usuario(db.Model, UserMixin):
    """Modelo para usuarios administrativos y personal de Yavirac."""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    seguimientos = db.relationship('Seguimiento', backref='usuario', lazy=True)
    observaciones = db.relationship('Observacion', backref='usuario', lazy=True)
    documentos_subidos = db.relationship('Documento', backref='verificador', lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<Usuario {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[Usuario]:
    return Usuario.query.get(int(user_id))


class Carrera(db.Model):
    """Modelo para las carreras del instituto."""
    __tablename__ = 'carreras'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)

    estudiantes = db.relationship('Estudiante', backref='carrera', lazy=True)
    malla_link = db.Column(db.String(500), nullable=True)
    syllabus_link = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Carrera {self.code} - {self.name}>"


class CicloAcademico(db.Model):
    """Modelo para los ciclos académicos (periodos lectivos)."""
    __tablename__ = 'ciclos_academicos'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='vigente')  # 'vigente', 'cerrado'

    # Relación
    estudiantes = db.relationship('Estudiante', backref='ciclo', lazy=True)

    def __repr__(self) -> str:
        return f"<CicloAcademico {self.code} - {self.name}>"


class Estudiante(db.Model):
    """Modelo para los estudiantes que solicitan la homologación."""
    __tablename__ = 'estudiantes'

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    carrera_id = db.Column(db.Integer, db.ForeignKey('carreras.id'), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_academicos.id'), nullable=True)
    token = db.Column(db.String(100), unique=True, nullable=True)  # Token de acceso rápido para portal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)  # Para pre-registros en línea

    # Relaciones
    solicitudes = db.relationship('Solicitud', backref='estudiante', cascade="all, delete-orphan", lazy=True)

    @property
    def fullname(self) -> str:
        return f"{self.name} {self.lastname}"

    def __repr__(self) -> str:
        return f"<Estudiante {self.cedula} - {self.fullname}>"


class Solicitud(db.Model):
    """Modelo para la solicitud de homologación de un estudiante."""
    __tablename__ = 'solicitudes'

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(50), default='Pendiente Documentos')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    documentos = db.relationship('Documento', backref='solicitud', cascade="all, delete-orphan", lazy=True)
    seguimientos = db.relationship('Seguimiento', backref='solicitud', cascade="all, delete-orphan", lazy=True)
    observaciones = db.relationship('Observacion', backref='solicitud', cascade="all, delete-orphan", lazy=True)

    def __repr__(self) -> str:
        return f"<Solicitud {self.code} - Estado: {self.status}>"


class TipoDocumento(db.Model):
    """Modelo para definir el tipo de documento requerido (Checklist)."""
    __tablename__ = 'tipos_documentos'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250))
    required = db.Column(db.Boolean, default=True)

    documentos = db.relationship('Documento', backref='tipo_documento', lazy=True)

    def __repr__(self) -> str:
        return f"<TipoDocumento {self.name} (Requerido: {self.required})>"


class Documento(db.Model):
    """Modelo para guardar la carga física de cada documento de la solicitud."""
    __tablename__ = 'documentos'

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes.id'), nullable=False)
    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipos_documentos.id'), nullable=False)
    file_path = db.Column(db.String(250), nullable=True)
    filename = db.Column(db.String(150), nullable=True)
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='Pendiente')  # Pendiente, Aprobado, Rechazado
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Null si subió el estudiante
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Documento {self.filename} - Version: {self.version} - Estado: {self.status}>"


class Seguimiento(db.Model):
    """Modelo para registrar el historial de acciones y auditoría de la solicitud."""
    __tablename__ = 'seguimientos'

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Null si es acción de sistema/estudiante
    action = db.Column(db.String(100), nullable=False)  # ej: 'Cambio de Estado', 'Documento Subido'
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Seguimiento {self.action} para Solicitud {self.solicitud_id}>"


class Observacion(db.Model):
    """Modelo para registrar notas internas u observaciones generales sobre la carpeta."""
    __tablename__ = 'observaciones'

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Observacion en Solicitud {self.solicitud_id} por Usuario {self.user_id}>"


class FAQCategoria(db.Model):
    """Categoría para organizar las preguntas frecuentes."""
    __tablename__ = 'faq_categorias'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    faqs = db.relationship('FAQ', backref='categoria', lazy=True)

    def __repr__(self) -> str:
        return f"<FAQCategoria {self.name}>"


class FAQ(db.Model):
    """Modelo para las preguntas frecuentes auto-servicio."""
    __tablename__ = 'faqs'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(250), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('faq_categorias.id'), nullable=False)
    views_count = db.Column(db.Integer, default=0)

    def __repr__(self) -> str:
        return f"<FAQ {self.question[:30]}...>"


class AuditLog(db.Model):
    """Log de auditoría general del sistema."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    table_name = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # INSERT, UPDATE, DELETE
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} en {self.table_name}>"
