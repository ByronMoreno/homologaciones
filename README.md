# homologaciones

HomologaSys es un sistema premium de gestión y seguimiento de carpetas de homologación para el instituto superior tecnológico Yavirac. Permite a los estudiantes realizar pre-registros, consultar los requisitos del checklist digital, descargar mallas, programas de estudio (syllabus) y generar certificados en línea de no poseer terceras matrículas ni sanciones. 

Asimismo, brinda a la secretaría del instituto una consola administrativa (CRM) con control total sobre el estado de las carpetas, aprobación de expedientes físicos, estadísticas de avance, gestión de carreras y periodos académicos (Ciclos).

---

## 🛠️ Stack Tecnológico
*   **Backend:** Python 3.10 + Flask + SQLAlchemy (ORM)
*   **Base de Datos:** PostgreSQL 15 (Producción/Docker) | SQLite (Pruebas Locales)
*   **Migraciones:** Flask-Migrate (Alembic)
*   **Frontend:** HTML5 + CSS3 (Premium Glassmorphism Design) + Bootstrap 5 + Bootstrap Icons + HTMX (para peticiones dinámicas)
*   **Pruebas:** Unittest de Python
*   **Contenedores:** Docker & Docker Compose

---

## 🚀 Puesta en Marcha (Modo Desarrollo con Docker)

### 1. Requisitos
Asegúrate de tener instalado en tu sistema:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Construir e iniciar contenedores
Desde la raíz del proyecto, ejecuta:
```bash
docker-compose up -d --build
```
Esto levantará:
*   El servidor web Flask en: [http://localhost:5000](http://localhost:5000)
*   El servidor de base de datos PostgreSQL 15 en: `localhost:5432`

### 3. Ejecutar Migraciones de Base de Datos
Para generar la estructura de tablas relacionales en la base de datos PostgreSQL, ejecuta:
```bash
docker-compose exec web flask db upgrade
```

### 4. Inicializar Datos Oficiales (Seeder)
Puebla la base de datos con las carreras oficiales, roles, FAQs de auto-servicio, requisitos de checklist digital y un periodo académico vigente (Ciclo Académico 2026-1) con:
```bash
docker-compose exec web flask seed-db
```

### 5. Cuentas de Acceso por Defecto (CRM de Secretaría)
*   **Administrador:** `admin` / `admin123`
*   **Secretaria:** `secretaria` / `sec123`

---

## 🧪 Pruebas Unitarias e Integración
Puedes ejecutar el set de validaciones completas dentro de la burbuja del contenedor ejecutando:
```bash
docker-compose exec web python -m unittest tests/test_app.py
```
