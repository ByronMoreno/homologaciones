import unittest
from app import create_app
from extensions import db
from app.models import Rol, Carrera, Estudiante, Solicitud, TipoDocumento, Documento, CicloAcademico

class HomologaSysTestCase(unittest.TestCase):
    def setUp(self):
        # Usar la configuración de pruebas (base de datos en memoria SQLite)
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Crear todas las tablas
        db.create_all()
        
        # Sembrar datos necesarios para las pruebas
        self.seed_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_test_data(self):
        # Crear Rol
        self.rol_admin = Rol(name="Administrador", description="Admin test")
        db.session.add(self.rol_admin)
        
        # Crear Carrera
        self.carrera = Carrera(name="Desarrollo de Software", code="DS")
        db.session.add(self.carrera)
        
        # Crear Tipo de Documento
        self.tipo_doc = TipoDocumento(name="Cédula", description="Copia de cédula", required=True)
        db.session.add(self.tipo_doc)
        db.session.commit()
        
        # Crear Usuario Admin para pruebas de vistas
        from app.models import Usuario
        self.admin_user = Usuario(
            username="admin",
            email="admin@test.com",
            role_id=self.rol_admin.id,
            active=True
        )
        self.admin_user.set_password("password")
        db.session.add(self.admin_user)
        db.session.commit()

    def test_app_creation(self):
        """Verifica que la app se crea correctamente en modo test."""
        self.assertTrue(self.app.config['TESTING'])

    def test_estudiante_y_solicitud_creation(self):
        """Verifica que un estudiante y su solicitud se crean correctamente."""
        estudiante = Estudiante(
            cedula="1726543890",
            name="Juan",
            lastname="Perez",
            email="juan.perez@test.com",
            phone="0987654321",
            carrera_id=self.carrera.id,
            token="test-token-123"
        )
        db.session.add(estudiante)
        db.session.flush()
        
        solicitud = Solicitud(
            estudiante_id=estudiante.id,
            code="HOM-1726543890-2026",
            status="Pendiente Documentos"
        )
        db.session.add(solicitud)
        db.session.commit()
        
        self.assertIsNotNone(estudiante.id)
        self.assertIsNotNone(solicitud.id)
        self.assertEqual(solicitud.code, "HOM-1726543890-2026")
        self.assertEqual(solicitud.status, "Pendiente Documentos")

    def test_document_versioning(self):
        """Verifica que la carga de un documento guarda la versión correcta."""
        estudiante = Estudiante(
            cedula="1726543890",
            name="Juan",
            lastname="Perez",
            email="juan.perez@test.com",
            carrera_id=self.carrera.id
        )
        db.session.add(estudiante)
        db.session.flush()
        
        solicitud = Solicitud(
            estudiante_id=estudiante.id,
            code="HOM-1726543890-2026"
        )
        db.session.add(solicitud)
        db.session.flush()
        
        # Carga versión 1
        doc_v1 = Documento(
            solicitud_id=solicitud.id,
            tipo_documento_id=self.tipo_doc.id,
            file_path="1726543890_1_v1.pdf",
            filename="cedula.pdf",
            version=1,
            status="Pendiente"
        )
        db.session.add(doc_v1)
        db.session.commit()
        
        db_doc = Documento.query.filter_by(solicitud_id=solicitud.id, tipo_documento_id=self.tipo_doc.id).first()
        self.assertEqual(db_doc.version, 1)
        self.assertEqual(db_doc.filename, "cedula.pdf")

    def test_physical_checklist_and_notes(self):
        """Verifica que se pueden registrar entregas físicas sin archivo y con notas de observación."""
        estudiante = Estudiante(
            cedula="1726543890",
            name="Juan",
            lastname="Perez",
            email="juan.perez@test.com",
            carrera_id=self.carrera.id
        )
        db.session.add(estudiante)
        db.session.flush()
        
        solicitud = Solicitud(
            estudiante_id=estudiante.id,
            code="HOM-1726543890-2026"
        )
        db.session.add(solicitud)
        db.session.flush()
        
        # Guardar una entrega física con notas (ej: "falta de sello")
        doc_checklist = Documento(
            solicitud_id=solicitud.id,
            tipo_documento_id=self.tipo_doc.id,
            file_path=None,
            filename=None,
            version=1,
            status="Observado",
            notes="Falta de sello de secretaría"
        )
        db.session.add(doc_checklist)
        db.session.commit()
        
        db_doc = Documento.query.filter_by(solicitud_id=solicitud.id, tipo_documento_id=self.tipo_doc.id).first()
        self.assertIsNone(db_doc.file_path)
        self.assertIsNone(db_doc.filename)
        self.assertEqual(db_doc.status, "Observado")
        self.assertEqual(db_doc.notes, "Falta de sello de secretaría")

    def test_carrera_drive_links(self):
        """Verifica que los enlaces de Drive de mallas y syllabus en Carrera se guardan correctamente."""
        self.carrera.malla_link = "https://drive.google.com/drive/folders/malla-link"
        self.carrera.syllabus_link = "https://drive.google.com/drive/folders/syllabus-link"
        db.session.commit()
        
        db_carrera = Carrera.query.filter_by(code="DS").first()
        self.assertEqual(db_carrera.malla_link, "https://drive.google.com/drive/folders/malla-link")
        self.assertEqual(db_carrera.syllabus_link, "https://drive.google.com/drive/folders/syllabus-link")

    def test_student_registration_and_approval(self):
        """Verifica que el auto-registro se guarda como no aprobado y se activa correctamente al aprobarse."""
        estudiante = Estudiante(
            cedula="1726543891",
            name="Maria",
            lastname="Gomez",
            email="maria@test.com",
            carrera_id=self.carrera.id,
            approved=False  # Auto-registro
        )
        db.session.add(estudiante)
        db.session.commit()
        
        # Debe estar inactivo
        db_student = Estudiante.query.filter_by(cedula="1726543891").first()
        self.assertFalse(db_student.approved)
        
        # Al ser aprobado por secretaría
        db_student.approved = True
        solicitud = Solicitud(
            estudiante_id=db_student.id,
            code="HOM-1726543891-2026",
            status="Pendiente Documentos"
        )
        db.session.add(solicitud)
        db.session.commit()
        
        # Validar activación
        db_student_approved = Estudiante.query.filter_by(cedula="1726543891").first()
        self.assertTrue(db_student_approved.approved)
        self.assertIsNotNone(db_student_approved.solicitudes)
        self.assertEqual(db_student_approved.solicitudes[0].status, "Pendiente Documentos")

    def test_academic_cycles(self):
        """Verifica que el ciclo académico se crea, que solo hay uno vigente y que los estudiantes se vinculan por defecto."""
        # Crear primer ciclo vigente
        ciclo1 = CicloAcademico(code="2026-1", name="Ciclo 2026-1", status="vigente")
        db.session.add(ciclo1)
        db.session.commit()
        
        # Crear segundo ciclo vigente (debe poner el anterior en cerrado)
        CicloAcademico.query.update({CicloAcademico.status: 'cerrado'})
        ciclo2 = CicloAcademico(code="2026-2", name="Ciclo 2026-2", status="vigente")
        db.session.add(ciclo2)
        db.session.commit()
        
        # Verificar que el ciclo1 ahora esté 'cerrado' y el ciclo2 esté 'vigente'
        self.assertEqual(ciclo1.status, "cerrado")
        self.assertEqual(ciclo2.status, "vigente")
        
        # Registrar estudiante y verificar que se vincula al vigente
        ciclo_vigente = CicloAcademico.query.filter_by(status='vigente').first()
        estudiante = Estudiante(
            cedula="1726543892",
            name="Luis",
            lastname="Perez",
            email="luis.perez@test.com",
            carrera_id=self.carrera.id,
            ciclo_id=ciclo_vigente.id if ciclo_vigente else None
        )
        db.session.add(estudiante)
        db.session.commit()
        
        self.assertEqual(estudiante.ciclo_id, ciclo2.id)
        self.assertEqual(estudiante.ciclo.code, "2026-2")

    def test_edit_and_delete_student_routes(self):
        """Verifica que las rutas de edición y eliminación de estudiantes funcionan correctamente."""
        # 1. Crear estudiante y solicitud
        estudiante = Estudiante(
            cedula="1726543899",
            name="Juan",
            lastname="Perez",
            email="juan@test.com",
            carrera_id=self.carrera.id
        )
        db.session.add(estudiante)
        db.session.flush()
        
        solicitud = Solicitud(
            estudiante_id=estudiante.id,
            code="HOM-1726543899-2026",
            status="Pendiente Documentos"
        )
        db.session.add(solicitud)
        db.session.commit()
        
        # 2. Utilizar el cliente de pruebas para iniciar sesión
        client = self.app.test_client()
        login_res = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'password'
        }, follow_redirects=True)
        
        # 3. Editar estudiante
        edit_res = client.post(f'/admin/estudiante/{estudiante.id}/editar-datos', data={
            'name': 'Juan Modificado',
            'lastname': 'Perez Modificado',
            'email': 'juan.modificado@test.com',
            'phone': '0999999999',
            'carrera_id': self.carrera.id,
            'ciclo_id': ''
        }, follow_redirects=True)
        
        # Verificar cambios
        db_student = Estudiante.query.get(estudiante.id)
        self.assertEqual(db_student.name, 'Juan Modificado')
        self.assertEqual(db_student.email, 'juan.modificado@test.com')
        
        # 4. Eliminar estudiante
        delete_res = client.post(f'/admin/estudiante/{estudiante.id}/eliminar-registro', follow_redirects=True)
        
        # Verificar eliminación
        db_student_deleted = Estudiante.query.get(estudiante.id)
        self.assertIsNone(db_student_deleted)
        db_solicitud_deleted = Solicitud.query.get(solicitud.id)
        self.assertIsNone(db_solicitud_deleted)

if __name__ == '__main__':
    unittest.main()
