import io
import csv
from flask import render_template, make_response
from flask_login import login_required
from extensions import db
from app.reports import reports_bp
from app.models import Solicitud, Estudiante, Carrera

@reports_bp.route('/')
@login_required
def index():
    # 1. Total de solicitudes por estado
    estados = ['Pendiente Documentos', 'Documentación Incompleta', 'Documentación Completa', 'Sellado Secretaría', 'Entregado a Universidad', 'Matriculado']
    stats_estado = {}
    for est in estados:
        stats_estado[est] = Solicitud.query.filter_by(status=est).count()

    # 2. Solicitudes por carrera
    carreras = Carrera.query.all()
    stats_carrera = {}
    for carr in carreras:
        stats_carrera[carr.name] = Solicitud.query.join(Estudiante).filter(Estudiante.carrera_id == carr.id).count()

    # 3. Métricas clave
    total_estudiantes = Estudiante.query.count()
    total_finalizados = Solicitud.query.filter_by(status='Matriculado').count()
    
    # Tasa de conversión
    tasa_conversion = int((total_finalizados / total_estudiantes) * 100) if total_estudiantes > 0 else 0

    return render_template(
        'reports/index.html',
        stats_estado=stats_estado,
        stats_carrera=stats_carrera,
        total_estudiantes=total_estudiantes,
        total_finalizados=total_finalizados,
        tasa_conversion=tasa_conversion,
        active_page='reports'
    )

@reports_bp.route('/exportar/csv')
@login_required
def exportar_csv():
    # Crear un buffer en memoria
    output = io.StringIO()
    # Usar utf-8-sig para que Excel reconozca tildes y eñes correctamente
    writer = csv.writer(output, delimiter=';')
    
    # Escribir cabecera
    writer.writerow([
        'Código Solicitud', 
        'Cédula', 
        'Nombres', 
        'Apellidos', 
        'Carrera', 
        'Estado Actual', 
        'Fecha Registro', 
        'Última Modificación'
    ])
    
    # Obtener todas las solicitudes
    solicitudes = Solicitud.query.join(Estudiante).order_by(Solicitud.created_at.desc()).all()
    
    for sol in solicitudes:
        writer.writerow([
            sol.code,
            sol.estudiante.cedula,
            sol.estudiante.name,
            sol.estudiante.lastname,
            sol.estudiante.carrera.name,
            sol.status,
            sol.created_at.strftime('%d/%m/%Y %H:%M'),
            sol.updated_at.strftime('%d/%m/%Y %H:%M')
        ])
        
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_homologaciones.csv'
    response.headers['Content-type'] = 'text/csv; charset=utf-8-sig'
    return response
