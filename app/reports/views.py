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

@reports_bp.route('/exportar/pdf')
@login_required
def exportar_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    # 1. Obtener datos
    total_estudiantes = Estudiante.query.count()
    por_revisar = Solicitud.query.filter(Solicitud.status.in_(['Pendiente Documentos', 'Documentación Completa'])).count()
    en_proceso = Solicitud.query.filter(Solicitud.status.in_(['Documentación Incompleta', 'Sellado Secretaría', 'Entregado a Universidad'])).count()
    matriculados = Solicitud.query.filter_by(status='Matriculado').count()
    
    solicitudes = Solicitud.query.join(Estudiante).order_by(Solicitud.created_at.desc()).all()
    
    # 2. Generar PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1e293b')
    )
    
    bold_cell_style = ParagraphStyle(
        'TableBoldCell',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )

    story.append(Paragraph("<b>Portal de Gestión y Homologación - Yavirac - UNIB.E</b>", title_style))
    story.append(Paragraph("Reporte Ejecutivo de Expedientes de Homologación", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Summary Metrics Cards
    metric_data = [
        [
            Paragraph("<b>Total Estudiantes</b>", cell_style),
            Paragraph("<b>Por Revisar</b>", cell_style),
            Paragraph("<b>En Proceso</b>", cell_style),
            Paragraph("<b>Matriculados UNIB.E</b>", cell_style)
        ],
        [
            Paragraph(f"<font size=13><b>{total_estudiantes}</b></font>", bold_cell_style),
            Paragraph(f"<font size=13 color='#e11d48'><b>{por_revisar}</b></font>", bold_cell_style),
            Paragraph(f"<font size=13 color='#ea580c'><b>{en_proceso}</b></font>", bold_cell_style),
            Paragraph(f"<font size=13 color='#16a34a'><b>{matriculados}</b></font>", bold_cell_style)
        ]
    ]
    
    metric_table = Table(metric_data, colWidths=[135, 135, 135, 135])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    
    story.append(metric_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("<b>Detalle de Expedientes y Alumnos</b>", ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=11, spaceAfter=8, textColor=colors.HexColor('#0f172a'))))
    
    # Detailed Table Columns: Código, Estudiante, Cédula, Carrera, Ciclo, Estado
    table_data = [
        [
            Paragraph("<b>Código</b>", header_style),
            Paragraph("<b>Estudiante</b>", header_style),
            Paragraph("<b>Cédula</b>", header_style),
            Paragraph("<b>Carrera en la que se Graduó</b>", header_style),
            Paragraph("<b>Ciclo Académico</b>", header_style),
            Paragraph("<b>Estado Actual</b>", header_style)
        ]
    ]
    
    for sol in solicitudes:
        ciclo_nom = sol.estudiante.ciclo.name if sol.estudiante.ciclo else 'N/A'
        table_data.append([
            Paragraph(sol.code, cell_style),
            Paragraph(f"{sol.estudiante.lastname} {sol.estudiante.name}", cell_style),
            Paragraph(sol.estudiante.cedula, cell_style),
            Paragraph(sol.estudiante.carrera.name, cell_style),
            Paragraph(ciclo_nom, cell_style),
            Paragraph(f"<b>{sol.status}</b>", cell_style)
        ])
        
    detailed_table = Table(table_data, colWidths=[65, 120, 60, 120, 95, 80])
    
    t_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ])
    
    for i in range(1, len(table_data)):
        bg_color = colors.HexColor('#f8fafc') if i % 2 == 0 else colors.white
        t_style.add('BACKGROUND', (0, i), (-1, i), bg_color)
        
    detailed_table.setStyle(t_style)
    story.append(detailed_table)
    
    doc.build(story)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_homologaciones.pdf'
    response.headers['Content-type'] = 'application/pdf'
    return response
