import click
from flask.cli import with_appcontext
from extensions import db
from app.models import Rol, Carrera, TipoDocumento, Usuario, FAQCategoria, FAQ, Documento, CicloAcademico

@click.command("seed-db")
@with_appcontext
def seed_db():
    """Puebla la base de datos con los datos iniciales necesarios."""
    click.echo("Iniciando la siembra de la base de datos...")

    # 1. Crear Roles
    roles_data = [
        {"name": "Administrador", "description": "Acceso total al sistema y configuraciones."},
        {"name": "Secretaria", "description": "Gestión de carpetas, checklists y notificaciones de estudiantes."},
        {"name": "Consulta", "description": "Visualización y reportes sin permisos de edición."}
    ]
    roles = {}
    for r_info in roles_data:
        rol = Rol.query.filter_by(name=r_info["name"]).first()
        if not rol:
            rol = Rol(name=r_info["name"], description=r_info["description"])
            db.session.add(rol)
            click.echo(f"Rol creado: {r_info['name']}")
        roles[r_info["name"]] = rol
    db.session.commit()

    # 2. Crear Carreras con Enlaces de Drive para Malla y Syllabus
    carreras_data = [
        {
            "name": "Desarrollo de Software", 
            "code": "DS",
            "malla_link": "https://drive.google.com/drive/folders/1DS-malla-drive-link-ficticio",
            "syllabus_link": "https://drive.google.com/drive/folders/1DS-syllabus-drive-link-ficticio"
        },
        {
            "name": "Diseño de Modas", 
            "code": "DM",
            "malla_link": "https://drive.google.com/drive/folders/2DM-malla-drive-link-ficticio",
            "syllabus_link": "https://drive.google.com/drive/folders/2DM-syllabus-drive-link-ficticio"
        },
        {
            "name": "Gastronomía", 
            "code": "GA",
            "malla_link": "https://drive.google.com/drive/folders/3GA-malla-drive-link-ficticio",
            "syllabus_link": "https://drive.google.com/drive/folders/3GA-syllabus-drive-link-ficticio"
        },
        {
            "name": "Guía Nacional de Turismo", 
            "code": "GT",
            "malla_link": "https://drive.google.com/drive/folders/4GT-malla-drive-link-ficticio",
            "syllabus_link": "https://drive.google.com/drive/folders/4GT-syllabus-drive-link-ficticio"
        },
        {
            "name": "Marketing Digital", 
            "code": "MD",
            "malla_link": "https://drive.google.com/drive/folders/5MD-malla-drive-link-ficticio",
            "syllabus_link": "https://drive.google.com/drive/folders/5MD-syllabus-drive-link-ficticio"
        }
    ]
    for c_info in carreras_data:
        carrera = Carrera.query.filter_by(code=c_info["code"]).first()
        if not carrera:
            carrera = Carrera(
                name=c_info["name"], 
                code=c_info["code"],
                malla_link=c_info["malla_link"],
                syllabus_link=c_info["syllabus_link"]
            )
            db.session.add(carrera)
            click.echo(f"Carrera creada: {c_info['name']}")
        else:
            carrera.malla_link = c_info["malla_link"]
            carrera.syllabus_link = c_info["syllabus_link"]
            click.echo(f"Carrera actualizada con enlaces de Drive: {c_info['name']}")
    db.session.commit()

    # 2b. Crear Ciclo Académico Vigente por defecto
    ciclo_vigente = CicloAcademico.query.filter_by(status='vigente').first()
    if not ciclo_vigente:
        ciclo_vigente = CicloAcademico(
            code="2026-1",
            name="Periodo Académico 2026-1",
            status="vigente"
        )
        db.session.add(ciclo_vigente)
        db.session.commit()
        click.echo("Ciclo académico vigente por defecto creado: Periodo Académico 2026-1")
    
    # Vincular estudiantes sin ciclo al ciclo vigente
    from app.models import Estudiante
    estudiantes_sin_ciclo = Estudiante.query.filter_by(ciclo_id=None).all()
    if estudiantes_sin_ciclo:
        for est in estudiantes_sin_ciclo:
            est.ciclo_id = ciclo_vigente.id
        db.session.commit()
        click.echo(f"Vinculados {len(estudiantes_sin_ciclo)} estudiantes al ciclo vigente {ciclo_vigente.code}.")

    # 3. Crear Tipos de Documentos (Checklist Físico y Recursos)
    # Limpiamos tablas dependientes en desarrollo para recrear el listado oficial
    try:
        db.session.query(Documento).delete()
        db.session.query(TipoDocumento).delete()
        db.session.commit()
        click.echo("Checklist de documentos antiguos limpiado.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Aviso en limpieza de checklist: {str(e)}")

    documentos_data = [
        {"name": "Cédula de Identidad y Papeleta de Votación", "description": "Copia legible a color de la cédula y del último certificado de votación en un solo documento físico.", "required": True},
        {"name": "Título de Bachiller Notarizado", "description": "Copia notarizada del título de bachiller o acta de grado.", "required": True},
        {"name": "Fotos tamaño carnet (3)", "description": "Tres fotos recientes tamaño carnet a color en fondo blanco para el expediente físico.", "required": True},
        {"name": "Certificado de Inglés", "description": "Certificado físico de aprobación del nivel de suficiencia en inglés.", "required": True},
        {"name": "Certificado de Vinculación con la Sociedad", "description": "Certificado oficial de finalización de horas de vinculación.", "required": True},
        {"name": "Récord Académico", "description": "Historial académico oficial cargado por secretaría. El estudiante debe descargarlo e imprimirlo.", "required": True},
        {"name": "Certificado de no poseer terceras matrículas y sanciones", "description": "Certificado generado en línea por el estudiante desde su portal. Debe descargarse e imprimirse.", "required": True},
        {"name": "Malla Curricular", "description": "Malla académica de la carrera. Descargar desde el enlace de Drive provisto, imprimir y entregar.", "required": True},
        {"name": "Syllabus / Programas de Estudio", "description": "Programas analíticos aprobados de la carrera. Descargar desde el enlace de Drive, imprimir y entregar.", "required": True}
    ]
    for doc_info in documentos_data:
        t_doc = TipoDocumento(
            name=doc_info["name"],
            description=doc_info["description"],
            required=doc_info["required"]
        )
        db.session.add(t_doc)
        click.echo(f"Tipo de Documento creado: {doc_info['name']}")
    db.session.commit()

    # 4. Crear Usuario Administrador por Defecto
    admin_user = Usuario.query.filter_by(username="admin").first()
    if not admin_user:
        admin_user = Usuario(
            username="admin",
            email="admin@yavirac.edu.ec",
            role_id=roles["Administrador"].id,
            active=True
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        click.echo("Usuario Administrador por defecto creado (admin / admin123)")
        
    # Crear Usuario Secretaria por Defecto
    sec_user = Usuario.query.filter_by(username="secretaria").first()
    if not sec_user:
        sec_user = Usuario(
            username="secretaria",
            email="secretaria@yavirac.edu.ec",
            role_id=roles["Secretaria"].id,
            active=True
        )
        sec_user.set_password("sec123")
        db.session.add(sec_user)
        click.echo("Usuario Secretaria por defecto creado (secretaria / sec123)")
    db.session.commit()

    # 5. Crear FAQs y Categorías
    cat_doc = FAQCategoria.query.filter_by(name="Documentación").first()
    if not cat_doc:
        cat_doc = FAQCategoria(name="Documentación")
        db.session.add(cat_doc)
    
    cat_proc = FAQCategoria.query.filter_by(name="Proceso").first()
    if not cat_proc:
        cat_proc = FAQCategoria(name="Proceso")
        db.session.add(cat_proc)
    db.session.commit()

    faqs_data = [
        {
            "question": "¿En qué formato debo subir los documentos?",
            "answer": "Todos los documentos deben ser escaneados y subidos en formato PDF legible, a excepción de las fotos tamaño carnet que pueden ser imágenes (PNG/JPG). El peso máximo por archivo es de 16MB.",
            "category_id": cat_doc.id
        },
        {
            "question": "¿Qué hago si no tengo el Certificado de Vinculación?",
            "answer": "Debes solicitarlo directamente al Coordinador de Vinculación de tu carrera en Yavirac. Es un requisito obligatorio para que UNIB.E acepte tu expediente de homologación.",
            "category_id": cat_doc.id
        },
        {
            "question": "¿Cuánto tiempo tarda la revisión de Secretaría de Yavirac?",
            "answer": "Una vez que subas todos tus documentos requeridos, la secretaría validará tu carpeta en un plazo de 3 a 5 días laborables. Recibirás un correo electrónico indicando si tu carpeta fue Aceptada o si algún documento fue Observado.",
            "category_id": cat_proc.id
        },
        {
            "question": "¿Cómo sé si mis documentos fueron aprobados?",
            "answer": "Puedes ingresar al Portal del Estudiante con tu cédula y el token de acceso. Allí verás el checklist de documentos; cada uno tendrá una marca verde (Aprobado), azul (Pendiente de revisión) o roja (Rechazado/Observado con un comentario del motivo).",
            "category_id": cat_proc.id
        }
    ]

    for faq_info in faqs_data:
        faq = FAQ.query.filter_by(question=faq_info["question"]).first()
        if not faq:
            faq = FAQ(
                question=faq_info["question"],
                answer=faq_info["answer"],
                category_id=faq_info["category_id"]
            )
            db.session.add(faq)
            click.echo(f"FAQ Creado: {faq_info['question'][:30]}...")
    db.session.commit()

    click.echo("¡Siembra de base de datos completada exitosamente!")
