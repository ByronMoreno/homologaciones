import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from app.homologaciones import homologaciones_bp
from app.models import Estudiante, Solicitud, Carrera, TipoDocumento, Documento, Seguimiento, Observacion, Usuario, CicloAcademico

# Helper para registrar seguimientos (historial)
def registrar_seguimiento(solicitud_id, action, details):
    ip_addr = request.remote_addr
    user_id = current_user.id if current_user.is_authenticated else None
    seguimiento = Seguimiento(
        solicitud_id=solicitud_id,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_addr
    )
    db.session.add(seguimiento)
    db.session.commit()

@homologaciones_bp.route('/')
@homologaciones_bp.route('/dashboard')
@login_required
def dashboard():
    # Obtener todas las carreras para el filtro
    carreras = Carrera.query.all()
    
    # Parámetros de búsqueda y filtros
    search_query = request.args.get('search', '').strip()
    carrera_id = request.args.get('carrera', '')
    
    # Query base para solicitudes
    query = Solicitud.query.join(Estudiante)
    
    if search_query:
        query = query.filter(
            or_(
                Estudiante.name.ilike(f'%{search_query}%'),
                Estudiante.lastname.ilike(f'%{search_query}%'),
                Estudiante.cedula.ilike(f'%{search_query}%'),
                Solicitud.code.ilike(f'%{search_query}%')
            )
        )
    
    if carrera_id:
        query = query.filter(Estudiante.carrera_id == int(carrera_id))
        
    solicitudes = query.order_by(Solicitud.updated_at.desc()).all()
    
    # Estadísticas para el dashboard
    total_estudiantes = Estudiante.query.filter_by(approved=True).count()
    solicitudes_activas = Solicitud.query.filter(Solicitud.status != 'Matriculado').count()
    pendientes_docs = Solicitud.query.filter(Solicitud.status == 'Pendiente Documentos').count()
    completadas = Solicitud.query.filter(Solicitud.status == 'Documentación Completa').count()
    selladas = Solicitud.query.filter(Solicitud.status == 'Sellado Secretaría').count()
    matriculados = Solicitud.query.filter(Solicitud.status == 'Matriculado').count()
    
    # Pre-registros pendientes
    pending_students = Estudiante.query.filter_by(approved=False).all()
    
    # Si la petición es de HTMX, retornar sólo la tabla parcial
    if request.headers.get('HX-Request'):
        return render_template('admin/partials/student_list.html', solicitudes=solicitudes)
        
    return render_template(
        'admin/dashboard.html',
        solicitudes=solicitudes,
        carreras=carreras,
        search_query=search_query,
        carrera_id=carrera_id,
        total_estudiantes=total_estudiantes,
        solicitudes_activas=solicitudes_activas,
        pendientes_docs=pendientes_docs,
        completadas=completadas,
        selladas=selladas,
        matriculados=matriculados,
        pending_students=pending_students,
        active_page='dashboard'
    )

@homologaciones_bp.route('/expediente/<int:solicitud_id>')
@login_required
def expediente(solicitud_id):
    solicitud = Solicitud.query.get_or_444(solicitud_id) if hasattr(Solicitud.query, 'get_or_444') else Solicitud.query.get_or_404(solicitud_id)
    
    # Asegurar que el estudiante tenga un token válido para no provocar errores de renderizado Jinja
    if not solicitud.estudiante.token:
        solicitud.estudiante.token = str(uuid.uuid4())
        db.session.commit()

    tipos_documentos = TipoDocumento.query.all()
    
    # Mapear los documentos subidos para el checklist
    docs_subidos = {doc.tipo_documento_id: doc for doc in solicitud.documentos}
    
    # Calcular el porcentaje de avance
    docs_requeridos = [td for td in tipos_documentos if td.required]
    docs_aprobados_count = sum(1 for doc in solicitud.documentos if doc.status == 'Aprobado' and doc.tipo_documento.required)
    
    progreso = int((docs_aprobados_count / len(docs_requeridos)) * 100) if docs_requeridos else 0
    
    # Enlace de WhatsApp Web con mensaje personalizado para el estudiante si faltan documentos o hay observaciones
    whatsapp_link = ""
    phone = solicitud.estudiante.phone
    if phone:
        # Limpiar caracteres del teléfono
        clean_phone = ''.join(c for c in phone if c.isdigit())
        if not clean_phone.startswith('593') and len(clean_phone) == 9: # Prefijo de Ecuador si falta
            clean_phone = '593' + clean_phone
        elif not clean_phone.startswith('593') and len(clean_phone) == 10 and clean_phone.startswith('0'):
            clean_phone = '593' + clean_phone[1:]
            
        portal_url = url_for('students.login_token', token=solicitud.estudiante.token, _external=True)
        message = f"Hola {solicitud.estudiante.name}, te saludamos de Secretaría de Yavirac. Te recordamos subir tus documentos pendientes o corregir las observaciones en tu expediente de homologación: {portal_url}"
        import urllib.parse
        whatsapp_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"

    carreras = Carrera.query.all()
    ciclos = CicloAcademico.query.all()

    return render_template(
        'admin/expediente.html',
        solicitud=solicitud,
        tipos_documentos=tipos_documentos,
        docs_subidos=docs_subidos,
        progreso=progreso,
        whatsapp_link=whatsapp_link,
        carreras=carreras,
        ciclos=ciclos,
        active_page='homologaciones'
    )

@homologaciones_bp.route('/nuevo-estudiante', methods=['GET', 'POST'])
@login_required
def nuevo_estudiante():
    carreras = Carrera.query.all()
    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        name = request.form.get('name', '').strip()
        lastname = request.form.get('lastname', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        carrera_id = request.form.get('carrera_id')

        # Validaciones de backend básicas
        if not (cedula and name and lastname and email and carrera_id):
            flash('Por favor llena todos los campos obligatorios.', 'error')
            return render_template('admin/nuevo_estudiante.html', carreras=carreras)

        if len(cedula) != 10:
            flash('La cédula debe tener exactamente 10 dígitos.', 'error')
            return render_template('admin/nuevo_estudiante.html', carreras=carreras)

        estudiante_existente = Estudiante.query.filter_by(cedula=cedula).first()
        if estudiante_existente:
            flash('Ya existe un estudiante registrado con esta cédula.', 'error')
            return render_template('admin/nuevo_estudiante.html', carreras=carreras)

        try:
            # Crear Estudiante
            ciclo_vigente = CicloAcademico.query.filter_by(status='vigente').first()
            token_acceso = str(uuid.uuid4())
            estudiante = Estudiante(
                cedula=cedula,
                name=name,
                lastname=lastname,
                email=email,
                phone=phone,
                carrera_id=int(carrera_id),
                ciclo_id=ciclo_vigente.id if ciclo_vigente else None,
                token=token_acceso,
                approved=True
            )
            db.session.add(estudiante)
            db.session.flush() # Para obtener el ID del estudiante

            # Crear Solicitud
            codigo_solicitud = f"HOM-{estudiante.cedula}-{datetime.now().year}"
            solicitud = Solicitud(
                estudiante_id=estudiante.id,
                code=codigo_solicitud,
                status='Pendiente Documentos'
            )
            db.session.add(solicitud)
            db.session.commit()

            registrar_seguimiento(
                solicitud_id=solicitud.id,
                action='Solicitud Creada',
                details=f"Carpeta creada manualmente por {current_user.username}. Token de acceso generado."
            )

            flash('Estudiante y solicitud de homologación creados con éxito.', 'success')
            return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar al estudiante: {str(e)}', 'error')
    return render_template('admin/nuevo_estudiante.html', carreras=carreras, active_page='homologaciones')

@homologaciones_bp.route('/expediente/<int:solicitud_id>/documento/<int:tipo_id>/marcar-estado', methods=['POST'])
@login_required
def marcar_estado_documento(solicitud_id, tipo_id):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    tipo_doc = TipoDocumento.query.get_or_404(tipo_id)
    
    nuevo_status = request.form.get('status')
    notes = request.form.get('notes', '').strip()
    
    if nuevo_status not in ['Aprobado', 'Observado', 'Pendiente']:
        flash('Estado de documento inválido.', 'error')
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        
    doc = Documento.query.filter_by(solicitud_id=solicitud.id, tipo_documento_id=tipo_id).first()
    
    if not doc:
        doc = Documento(
            solicitud_id=solicitud.id,
            tipo_documento_id=tipo_id,
            file_path=None,
            filename=None,
            status=nuevo_status,
            version=1,
            uploaded_by_user_id=current_user.id,
            notes=notes if notes else None
        )
        db.session.add(doc)
    else:
        doc.status = nuevo_status
        doc.uploaded_by_user_id = current_user.id
        doc.notes = notes if notes else None
        
    # Registrar en observaciones si es observado
    if nuevo_status == 'Observado':
        solicitud.status = 'Documentación Incompleta'
        obs = Observacion(
            solicitud_id=solicitud.id,
            user_id=current_user.id,
            comment=f"Documento '{tipo_doc.name}' OBSERVADO: {notes}"
        )
        db.session.add(obs)
        
    db.session.commit()
    
    # Log de seguimiento
    registrar_seguimiento(
        solicitud_id=solicitud.id,
        action=f"Doc {nuevo_status}",
        details=f"Estado de '{tipo_doc.name}' actualizado a '{nuevo_status}' por {current_user.username}. Nota: {notes if notes else 'Ninguna'}."
    )
    
    # Recalcular si toda la documentación obligatoria está completa y cambiar a 'Documentación Completa'
    tipos_requeridos = TipoDocumento.query.filter_by(required=True).all()
    docs_aprobados = Documento.query.filter_by(solicitud_id=solicitud.id, status='Aprobado').all()
    tipos_aprobados_ids = {d.tipo_documento_id for d in docs_aprobados}
    
    todos_aprobados = all(tr.id in tipos_aprobados_ids for tr in tipos_requeridos)
    if todos_aprobados and solicitud.status in ['Pendiente Documentos', 'Documentación Incompleta']:
        solicitud.status = 'Documentación Completa'
        db.session.commit()
        registrar_seguimiento(
            solicitud_id=solicitud.id,
            action='Cambio de Estado',
            details="Estado actualizado automáticamente a 'Documentación Completa' (todos los documentos requeridos aprobados)."
        )
        
    flash(f"Documento '{tipo_doc.name}' actualizado con éxito.", "success")
    return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))

@homologaciones_bp.route('/expediente/<int:solicitud_id>/documento/<int:tipo_id>/subir-record', methods=['POST'])
@login_required
def subir_record_admin(solicitud_id, tipo_id):
    import os
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    tipo_doc = TipoDocumento.query.get_or_404(tipo_id)
    
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        
    from app.students.views import allowed_file
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        doc = Documento.query.filter_by(solicitud_id=solicitud.id, tipo_documento_id=tipo_id).first()
        
        version = 1
        if doc and doc.version:
            version = doc.version + 1
            
        filename = f"record_{solicitud.estudiante.cedula}_v{version}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            
            if doc:
                doc.file_path = filename
                doc.filename = file.filename
                doc.version = version
                doc.status = 'Aprobado'
                doc.uploaded_at = datetime.utcnow()
                doc.uploaded_by_user_id = current_user.id
            else:
                doc = Documento(
                    solicitud_id=solicitud.id,
                    tipo_documento_id=tipo_id,
                    file_path=filename,
                    filename=file.filename,
                    version=version,
                    status='Aprobado',
                    uploaded_by_user_id=current_user.id
                )
                db.session.add(doc)
                
            db.session.commit()
            
            registrar_seguimiento(
                solicitud_id=solicitud.id,
                action='Récord Subido',
                details=f"El administrador subió el Récord Académico '{file.filename}' (v{version})."
            )
            
            # Recalcular si toda la documentación obligatoria está completa y cambiar a 'Documentación Completa'
            tipos_requeridos = TipoDocumento.query.filter_by(required=True).all()
            docs_aprobados = Documento.query.filter_by(solicitud_id=solicitud.id, status='Aprobado').all()
            tipos_aprobados_ids = {d.tipo_documento_id for d in docs_aprobados}
            
            todos_aprobados = all(tr.id in tipos_aprobados_ids for tr in tipos_requeridos)
            if todos_aprobados and solicitud.status in ['Pendiente Documentos', 'Documentación Incompleta']:
                solicitud.status = 'Documentación Completa'
                db.session.commit()
                registrar_seguimiento(
                    solicitud_id=solicitud.id,
                    action='Cambio de Estado',
                    details="Estado actualizado automáticamente a 'Documentación Completa' (todos los documentos requeridos aprobados)."
                )
                
            flash('Récord Académico subido y aprobado con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar el récord académico: {str(e)}', 'error')
    else:
        flash('Formato de archivo no permitido. Solo se aceptan PDFs o imágenes.', 'error')
        
    return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))

@homologaciones_bp.route('/expediente/<int:solicitud_id>/cambiar-estado', methods=['POST'])
@login_required
def cambiar_estado(solicitud_id):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    nuevo_estado = request.form.get('status')
    
    estados_validos = ['Pendiente Documentos', 'Documentación Incompleta', 'Documentación Completa', 'Sellado Secretaría', 'Entregado a Universidad', 'Matriculado']
    
    if nuevo_estado not in estados_validos:
        flash("Estado inválido proporcionado.", "error")
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        
    estado_anterior = solicitud.status
    solicitud.status = nuevo_estado
    db.session.commit()
    
    registrar_seguimiento(
        solicitud_id=solicitud.id,
        action='Cambio de Estado',
        details=f"Estado de la carpeta actualizado manualmente de '{estado_anterior}' a '{nuevo_estado}' por {current_user.username}."
    )
    
    flash(f"Estado de la solicitud actualizado a '{nuevo_estado}' con éxito.", "success")
    return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))

@homologaciones_bp.route('/expediente/<int:solicitud_id>/nota-interna', methods=['POST'])
@login_required
def agregar_nota(solicitud_id):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    comment = request.form.get('comment', '').strip()
    
    if not comment:
        flash("La nota interna no puede estar vacía.", "error")
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        
    observacion = Observacion(
        solicitud_id=solicitud.id,
        user_id=current_user.id,
        comment=f"Nota interna: {comment}"
    )
    db.session.add(observacion)
    db.session.commit()
    
    registrar_seguimiento(
        solicitud_id=solicitud.id,
        action='Nota Agregada',
        details=f"Nota interna agregada por {current_user.username}."
    )
    
    flash("Nota interna registrada con éxito.", "success")
    return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))

@homologaciones_bp.route('/carreras', methods=['GET'])
@login_required
def list_carreras():
    carreras = Carrera.query.all()
    return render_template('admin/carreras/list.html', carreras=carreras, active_page='carreras')

@homologaciones_bp.route('/carreras/nueva', methods=['GET', 'POST'])
@login_required
def nueva_carrera():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        malla_link = request.form.get('malla_link', '').strip()
        syllabus_link = request.form.get('syllabus_link', '').strip()
        
        if not code or not name:
            flash('Código y Nombre de la carrera son requeridos.', 'error')
            return render_template('admin/carreras/form.html', action_url=url_for('homologaciones.nueva_carrera'), title="Nueva Carrera", active_page='carreras')
            
        carrera_ex = Carrera.query.filter_by(code=code).first()
        if carrera_ex:
            flash(f'Ya existe una carrera con el código {code}.', 'error')
            return render_template('admin/carreras/form.html', action_url=url_for('homologaciones.nueva_carrera'), title="Nueva Carrera", active_page='carreras')
            
        try:
            carrera = Carrera(
                code=code,
                name=name,
                malla_link=malla_link if malla_link else None,
                syllabus_link=syllabus_link if syllabus_link else None
            )
            db.session.add(carrera)
            db.session.commit()
            flash(f'Carrera {name} creada con éxito.', 'success')
            return redirect(url_for('homologaciones.list_carreras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la carrera: {str(e)}', 'error')
            
    return render_template('admin/carreras/form.html', action_url=url_for('homologaciones.nueva_carrera'), title="Nueva Carrera", active_page='carreras')

@homologaciones_bp.route('/carreras/editar/<int:carrera_id>', methods=['GET', 'POST'])
@login_required
def editar_carrera(carrera_id):
    carrera = Carrera.query.get_or_404(carrera_id)
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        malla_link = request.form.get('malla_link', '').strip()
        syllabus_link = request.form.get('syllabus_link', '').strip()
        
        if not code or not name:
            flash('Código y Nombre de la carrera son requeridos.', 'error')
            return render_template('admin/carreras/form.html', carrera=carrera, action_url=url_for('homologaciones.editar_carrera', carrera_id=carrera.id), title="Editar Carrera", active_page='carreras')
            
        carrera_ex = Carrera.query.filter(Carrera.code == code, Carrera.id != carrera.id).first()
        if carrera_ex:
            flash(f'Ya existe otra carrera con el código {code}.', 'error')
            return render_template('admin/carreras/form.html', carrera=carrera, action_url=url_for('homologaciones.editar_carrera', carrera_id=carrera.id), title="Editar Carrera", active_page='carreras')
            
        try:
            carrera.code = code
            carrera.name = name
            carrera.malla_link = malla_link if malla_link else None
            carrera.syllabus_link = syllabus_link if syllabus_link else None
            db.session.commit()
            flash(f'Carrera {name} actualizada con éxito.', 'success')
            return redirect(url_for('homologaciones.list_carreras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la carrera: {str(e)}', 'error')
            
    return render_template('admin/carreras/form.html', carrera=carrera, action_url=url_for('homologaciones.editar_carrera', carrera_id=carrera.id), title="Editar Carrera", active_page='carreras')

@homologaciones_bp.route('/carreras/eliminar/<int:carrera_id>', methods=['POST'])
@login_required
def eliminar_carrera(carrera_id):
    carrera = Carrera.query.get_or_404(carrera_id)
    try:
        if len(carrera.estudiantes) > 0:
            flash(f'No se puede eliminar la carrera {carrera.name} porque tiene estudiantes registrados.', 'error')
            return redirect(url_for('homologaciones.list_carreras'))
            
        db.session.delete(carrera)
        db.session.commit()
        flash(f'Carrera {carrera.name} eliminada con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la carrera: {str(e)}', 'error')
    return redirect(url_for('homologaciones.list_carreras'))

@homologaciones_bp.route('/estudiante/<int:estudiante_id>/aprobar', methods=['POST'])
@login_required
def aprobar_estudiante(estudiante_id):
    student = Estudiante.query.get_or_404(estudiante_id)
    if student.approved:
        flash(f'El estudiante {student.name} ya está aprobado.', 'info')
        return redirect(url_for('homologaciones.dashboard'))
        
    try:
        student.approved = True
        
        if not student.token:
            student.token = str(uuid.uuid4())
            
        solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
        if not solicitud:
            codigo_solicitud = f"HOM-{student.cedula}-{datetime.now().year}"
            solicitud = Solicitud(
                estudiante_id=student.id,
                code=codigo_solicitud,
                status='Pendiente Documentos'
            )
            db.session.add(solicitud)
            db.session.flush()
            
        registrar_seguimiento(
            solicitud_id=solicitud.id,
            action='Registro Aprobado',
            details=f"El administrador/secretaria {current_user.username} aprobó y validó el pre-registro de {student.name} {student.lastname}."
        )
        
        db.session.commit()
        flash(f'Pre-registro de {student.name} {student.lastname} aprobado y validado con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al aprobar el registro: {str(e)}', 'error')
        
    return redirect(url_for('homologaciones.dashboard'))

@homologaciones_bp.route('/estudiante/<int:estudiante_id>/editar-datos', methods=['POST'])
@login_required
def editar_estudiante_post(estudiante_id):
    student = Estudiante.query.get_or_404(estudiante_id)
    name = request.form.get('name', '').strip()
    lastname = request.form.get('lastname', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    carrera_id = request.form.get('carrera_id')
    ciclo_id = request.form.get('ciclo_id')
    
    if not name or not lastname or not email or not carrera_id:
        flash('Nombre, Apellidos, Correo y Carrera son obligatorios.', 'error')
        solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
        if solicitud:
            return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
        return redirect(url_for('homologaciones.dashboard'))
        
    try:
        carrera_anterior = student.carrera.name
        carrera_nueva = Carrera.query.get(int(carrera_id))
        
        student.name = name
        student.lastname = lastname
        student.email = email
        student.phone = phone if phone else None
        student.carrera_id = int(carrera_id)
        student.ciclo_id = int(ciclo_id) if ciclo_id else None
        
        solicitud = Solicitud.query.filter_by(estudiante_id=student.id).first()
        if solicitud:
            details_str = f"Datos del estudiante actualizados por {current_user.username}."
            if carrera_anterior != carrera_nueva.name:
                details_str += f" Cambio de carrera: '{carrera_anterior}' a '{carrera_nueva.name}'."
                
            registrar_seguimiento(
                solicitud_id=solicitud.id,
                action='Datos Actualizados',
                details=details_str
            )
            
        db.session.commit()
        flash('Información del estudiante actualizada con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar información: {str(e)}', 'error')
        
    if solicitud:
        return redirect(url_for('homologaciones.expediente', solicitud_id=solicitud.id))
    return redirect(url_for('homologaciones.dashboard'))

@homologaciones_bp.route('/estudiante/<int:estudiante_id>/eliminar-registro', methods=['POST'])
@login_required
def eliminar_estudiante_post(estudiante_id):
    student = Estudiante.query.get_or_404(estudiante_id)
    try:
        name_str = f"{student.name} {student.lastname}"
        db.session.delete(student)
        db.session.commit()
        flash(f'El expediente y registro del estudiante {name_str} han sido eliminados con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el registro: {str(e)}', 'error')
    return redirect(url_for('homologaciones.dashboard'))

@homologaciones_bp.route('/ciclos', methods=['GET'])
@login_required
def list_ciclos():
    ciclos = CicloAcademico.query.all()
    return render_template('admin/ciclos/list.html', ciclos=ciclos, active_page='ciclos')

@homologaciones_bp.route('/ciclos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_ciclo():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        status = request.form.get('status', 'cerrado')
        
        if not code or not name:
            flash('Código y Nombre del ciclo son requeridos.', 'error')
            return render_template('admin/ciclos/form.html', action_url=url_for('homologaciones.nuevo_ciclo'), title="Nuevo Ciclo Académico", active_page='ciclos')
            
        ciclo_ex = CicloAcademico.query.filter_by(code=code).first()
        if ciclo_ex:
            flash(f'Ya existe un ciclo con el código {code}.', 'error')
            return render_template('admin/ciclos/form.html', action_url=url_for('homologaciones.nuevo_ciclo'), title="Nuevo Ciclo Académico", active_page='ciclos')
            
        try:
            if status == 'vigente':
                CicloAcademico.query.update({CicloAcademico.status: 'cerrado'})
                
            ciclo = CicloAcademico(
                code=code,
                name=name,
                status=status
            )
            db.session.add(ciclo)
            db.session.commit()
            flash(f'Ciclo Académico {name} creado con éxito.', 'success')
            return redirect(url_for('homologaciones.list_ciclos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el ciclo: {str(e)}', 'error')
            
    return render_template('admin/ciclos/form.html', action_url=url_for('homologaciones.nuevo_ciclo'), title="Nuevo Ciclo Académico", active_page='ciclos')

@homologaciones_bp.route('/ciclos/editar/<int:ciclo_id>', methods=['GET', 'POST'])
@login_required
def editar_ciclo(ciclo_id):
    ciclo = CicloAcademico.query.get_or_404(ciclo_id)
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        status = request.form.get('status', 'cerrado')
        
        if not code or not name:
            flash('Código y Nombre del ciclo son requeridos.', 'error')
            return render_template('admin/ciclos/form.html', ciclo=ciclo, action_url=url_for('homologaciones.editar_ciclo', ciclo_id=ciclo.id), title="Editar Ciclo Académico", active_page='ciclos')
            
        ciclo_ex = CicloAcademico.query.filter(CicloAcademico.code == code, CicloAcademico.id != ciclo.id).first()
        if ciclo_ex:
            flash(f'Ya existe otro ciclo con el código {code}.', 'error')
            return render_template('admin/ciclos/form.html', ciclo=ciclo, action_url=url_for('homologaciones.editar_ciclo', ciclo_id=ciclo.id), title="Editar Ciclo Académico", active_page='ciclos')
            
        try:
            if status == 'vigente':
                CicloAcademico.query.filter(CicloAcademico.id != ciclo.id).update({CicloAcademico.status: 'cerrado'})
                
            ciclo.code = code
            ciclo.name = name
            ciclo.status = status
            db.session.commit()
            flash(f'Ciclo Académico {name} actualizado con éxito.', 'success')
            return redirect(url_for('homologaciones.list_ciclos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el ciclo: {str(e)}', 'error')
            
    return render_template('admin/ciclos/form.html', ciclo=ciclo, action_url=url_for('homologaciones.editar_ciclo', ciclo_id=ciclo.id), title="Editar Ciclo Académico", active_page='ciclos')

@homologaciones_bp.route('/ciclos/eliminar/<int:ciclo_id>', methods=['POST'])
@login_required
def eliminar_ciclo(ciclo_id):
    ciclo = CicloAcademico.query.get_or_404(ciclo_id)
    try:
        if len(ciclo.estudiantes) > 0:
            flash(f'No se puede eliminar el ciclo {ciclo.name} porque tiene estudiantes registrados.', 'error')
            return redirect(url_for('homologaciones.list_ciclos'))
            
        db.session.delete(ciclo)
        db.session.commit()
        flash(f'Ciclo Académico {ciclo.name} eliminado con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el ciclo: {str(e)}', 'error')
    return redirect(url_for('homologaciones.list_ciclos'))

