import os
import uuid
from flask import render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import and_
from extensions import db
from app.students import students_bp
from app.models import Estudiante, Solicitud, TipoDocumento, Documento, Seguimiento, FAQCategoria, FAQ, Carrera, CicloAcademico

# Decorador de autenticación personalizado para estudiantes
def student_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            flash('Por favor ingresa tus credenciales para acceder al portal.', 'warning')
            return redirect(url_for('students.login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@students_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'student_id' in session:
        return redirect(url_for('students.dashboard'))
        
    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        
        if not cedula:
            flash('Ingresa tu número de cédula.', 'error')
            return render_template('students/login.html')
            
        student = Estudiante.query.filter_by(cedula=cedula).first()
        if not student:
            flash('Tu cédula no se encuentra registrada en el sistema. Te hemos redirigido para que completes tu pre-registro.', 'info')
            return redirect(url_for('students.registro', cedula=cedula))
            
        session['student_id'] = student.id
        flash(f'¡Bienvenido a tu portal, {student.name}!', 'success')
        return redirect(url_for('students.dashboard'))
        
    return render_template('students/login.html')

@students_bp.route('/acceso/<string:token>')
def login_token(token):
    student = Estudiante.query.filter_by(token=token).first()
    if not student:
        flash('El enlace de acceso ha expirado o es inválido.', 'error')
        return redirect(url_for('students.login'))
        
    session['student_id'] = student.id
    flash(f'¡Bienvenido a tu portal, {student.name}!', 'success')
    return redirect(url_for('students.dashboard'))

@students_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'student_id' in session:
        return redirect(url_for('students.dashboard'))
        
    carreras = Carrera.query.all()
    # Leer cédula del query string si fue redirigido
    cedula_prefilled = request.args.get('cedula', '').strip()
    
    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        name = request.form.get('name', '').strip()
        lastname = request.form.get('lastname', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        carrera_id = request.form.get('carrera_id')
        
        if not cedula or not name or not lastname or not email or not carrera_id:
            flash('Por favor completa todos los campos requeridos (*).', 'error')
            return render_template('students/registro.html', carreras=carreras, cedula_prefilled=cedula)
            
        # Verificar cédula duplicada
        existing_student = Estudiante.query.filter_by(cedula=cedula).first()
        if existing_student:
            flash('Este número de cédula ya se encuentra registrado. Inicia sesión directamente.', 'info')
            return redirect(url_for('students.login'))
            
        try:
            from datetime import datetime
            ciclo_vigente = CicloAcademico.query.filter_by(status='vigente').first()
            token_acceso = str(uuid.uuid4())
            student = Estudiante(
                cedula=cedula,
                name=name,
                lastname=lastname,
                email=email,
                phone=phone if phone else None,
                carrera_id=int(carrera_id),
                ciclo_id=ciclo_vigente.id if ciclo_vigente else None,
                token=token_acceso,
                approved=False  # Pendiente de validación formal en el CRM, pero puede entrar
            )
            db.session.add(student)
            db.session.flush()
            
            # Crear la solicitud inmediatamente para que pueda ver y subir el récord o generar certificado
            codigo_solicitud = f"HOM-{student.cedula}-{datetime.now().year}"
            solicitud = Solicitud(
                estudiante_id=student.id,
                code=codigo_solicitud,
                status='Pendiente Documentos'
            )
            db.session.add(solicitud)
            
            # Registrar bitácora
            seguimiento = Seguimiento(
                solicitud_id=solicitud.id,
                user_id=None,
                action='Pre-Registro',
                details=f"El estudiante se pre-registró de forma autónoma desde la web.",
                ip_address=request.remote_addr
            )
            db.session.add(seguimiento)
            db.session.commit()
            
            # Autologuear al estudiante directamente para su comodidad
            session['student_id'] = student.id
            flash('Pre-registro completado con éxito. Ya puedes ver tu proceso y mallas.', 'success')
            return redirect(url_for('students.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar tus datos: {str(e)}', 'error')
            
    return render_template('students/registro.html', carreras=carreras, cedula_prefilled=cedula_prefilled)

@students_bp.route('/dashboard')
@student_login_required
def dashboard():
    student = Estudiante.query.get(session['student_id'])
    if not student:
        session.pop('student_id', None)
        return redirect(url_for('students.login'))
        
    # Obtener la solicitud activa
    solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
    
    tipos_documentos = TipoDocumento.query.all()
    docs_subidos = {doc.tipo_documento_id: doc for doc in solicitud.documentos}
    
    # Progreso de la documentación obligatoria aprobada
    docs_requeridos = [td for td in tipos_documentos if td.required]
    docs_aprobados_count = sum(1 for doc in solicitud.documentos if doc.status == 'Aprobado' and doc.tipo_documento.required)
    progreso = int((docs_aprobados_count / len(docs_requeridos)) * 100) if docs_requeridos else 0
    
    # Cargar FAQs para el auto-servicio del estudiante
    faq_categorias = FAQCategoria.query.all()
    
    return render_template(
        'students/dashboard.html',
        student=student,
        solicitud=solicitud,
        tipos_documentos=tipos_documentos,
        docs_subidos=docs_subidos,
        progreso=progreso,
        faq_categorias=faq_categorias
    )

@students_bp.route('/subir-documento/<int:tipo_id>', methods=['POST'])
@student_login_required
def subir_documento(tipo_id):
    student = Estudiante.query.get(session['student_id'])
    solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
    tipo_doc = TipoDocumento.query.get_or_404(tipo_id)
    
    if not solicitud:
        flash('No se encontró una solicitud activa.', 'error')
        return redirect(url_for('students.dashboard'))
        
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('students.dashboard'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('students.dashboard'))
        
    if file and allowed_file(file.filename):
        # Obtener extensión
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Buscar si ya se subió antes para versionamiento
        doc_existente = Documento.query.filter_by(
            solicitud_id=solicitud.id,
            tipo_documento_id=tipo_id
        ).first()
        
        version = 1
        if doc_existente:
            version = doc_existente.version + 1
            # Si el documento estaba observado o rechazado, podemos re-utilizar el registro incrementando la versión y limpiando el estado
            # o crear un registro histórico, pero según el requisito: "nunca sobrescribir documentos, guardar historial".
            # Modificaremos el archivo en disco agregando la versión en el nombre para no sobreescribir el archivo previo en filesystem,
            # y actualizaremos los campos del registro existente.
            
        # Nombre de archivo único: cedula_tipoId_vVersion.extension
        filename = f"{student.cedula}_{tipo_id}_v{version}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            
            if doc_existente:
                doc_existente.file_path = filename
                doc_existente.filename = file.filename
                doc_existente.version = version
                doc_existente.status = 'Pendiente'  # Pasa de nuevo a revisión
                doc_existente.uploaded_at = datetime.utcnow()
                doc_existente.uploaded_by_user_id = None # Subido por el estudiante
            else:
                nuevo_doc = Documento(
                    solicitud_id=solicitud.id,
                    tipo_documento_id=tipo_id,
                    file_path=filename,
                    filename=file.filename,
                    version=version,
                    status='Pendiente'
                )
                db.session.add(nuevo_doc)
                
            # Log de seguimiento
            ip_addr = request.remote_addr
            seguimiento = Seguimiento(
                solicitud_id=solicitud.id,
                user_id=None,
                action='Documento Subido',
                details=f"El estudiante subió el documento '{tipo_doc.name}' (Versión {version}).",
                ip_address=ip_addr
            )
            db.session.add(seguimiento)
            
            # Si la solicitud estaba en "Documentación Incompleta", la regresamos a "Pendiente Documentos" para revisión de secretaría
            if solicitud.status == 'Documentación Incompleta':
                solicitud.status = 'Pendiente Documentos'
                
            db.session.commit()
            flash(f"Documento '{tipo_doc.name}' subido con éxito (Versión {version}).", 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar el archivo: {str(e)}", 'error')
    else:
        flash('Formato de archivo no permitido. Formatos aceptados: PDF, PNG, JPG, JPEG.', 'error')
        
    return redirect(url_for('students.dashboard'))

@students_bp.route('/logout')
def logout():
    session.pop('student_id', None)
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('students.login'))

@students_bp.route('/certificado-disciplinario')
@student_login_required
def certificado_disciplinario():
    import hashlib
    from datetime import datetime
    from app.models import Solicitud, Seguimiento, TipoDocumento, Documento
    
    student = Estudiante.query.get(session['student_id'])
    if not student:
        session.pop('student_id', None)
        return redirect(url_for('students.login'))
        
    # Formatear la fecha actual en español
    dt = datetime.now()
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio", 
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    fecha_actual = f"{dt.day} de {meses[dt.month - 1]} del {dt.year}"
    
    # Generar un hash único de verificación (MD5 abreviado)
    verif_payload = f"{student.cedula}_{dt.strftime('%Y%m%d%H%M')}"
    codigo_verif = hashlib.md5(verif_payload.encode('utf-8')).hexdigest()[:12].upper()
    
    # Registrar el seguimiento en la base de datos
    solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
    if solicitud:
        ip_addr = request.remote_addr
        seguimiento = Seguimiento(
            solicitud_id=solicitud.id,
            user_id=None,
            action='Certificado Generado',
            details=f"El estudiante generó en línea su certificado disciplinario (Verificación: {codigo_verif}).",
            ip_address=ip_addr
        )
        db.session.add(seguimiento)
        
        # Marcar automáticamente este requisito del checklist como Aprobado
        tipo_cert = TipoDocumento.query.filter(TipoDocumento.name.ilike('%terceras%')).first()
        if tipo_cert:
            doc_cert = Documento.query.filter_by(solicitud_id=solicitud.id, tipo_documento_id=tipo_cert.id).first()
            if not doc_cert:
                doc_cert = Documento(
                    solicitud_id=solicitud.id,
                    tipo_documento_id=tipo_cert.id,
                    file_path=None,
                    filename=None,
                    status='Aprobado',
                    version=1,
                    notes='Generado en línea por el estudiante.'
                )
                db.session.add(doc_cert)
            else:
                doc_cert.status = 'Aprobado'
                doc_cert.notes = 'Generado en línea por el estudiante.'
                
        db.session.commit()
        
    return render_template(
        'students/certificado.html',
        estudiante=student,
        fecha_actual=fecha_actual,
        codigo_verif=codigo_verif
    )
