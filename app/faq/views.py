from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from app.faq import faq_bp
from app.models import FAQ, FAQCategoria

@faq_bp.route('/')
@login_required
def index():
    faqs = FAQ.query.all()
    categorias = FAQCategoria.query.all()
    return render_template(
        'faq/admin_list.html', 
        faqs=faqs, 
        categorias=categorias,
        active_page='faq'
    )

@faq_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    categorias = FAQCategoria.query.all()
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        category_id = request.form.get('category_id')
        
        if not (question and answer and category_id):
            flash('Por favor completa todos los campos obligatorios.', 'error')
            return render_template('faq/form.html', categorias=categorias, faq=None)
            
        try:
            faq = FAQ(
                question=question,
                answer=answer,
                category_id=int(category_id)
            )
            db.session.add(faq)
            db.session.commit()
            flash('Pregunta frecuente creada con éxito.', 'success')
            return redirect(url_for('faq.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar la FAQ: {str(e)}', 'error')
            
    return render_template('faq/form.html', categorias=categorias, faq=None, active_page='faq')

@faq_bp.route('/editar/<int:faq_id>', methods=['GET', 'POST'])
@login_required
def editar(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    categorias = FAQCategoria.query.all()
    
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        category_id = request.form.get('category_id')
        
        if not (question and answer and category_id):
            flash('Por favor completa todos los campos obligatorios.', 'error')
            return render_template('faq/form.html', categorias=categorias, faq=faq)
            
        try:
            faq.question = question
            faq.answer = answer
            faq.category_id = int(category_id)
            db.session.commit()
            flash('Pregunta frecuente actualizada con éxito.', 'success')
            return redirect(url_for('faq.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la FAQ: {str(e)}', 'error')
            
    return render_template('faq/form.html', categorias=categorias, faq=faq, active_page='faq')

@faq_bp.route('/eliminar/<int:faq_id>', methods=['POST'])
@login_required
def eliminar(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    try:
        db.session.delete(faq)
        db.session.commit()
        flash('Pregunta frecuente eliminada con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la FAQ: {str(e)}', 'error')
    return redirect(url_for('faq.index'))

@faq_bp.route('/categoria/nueva', methods=['POST'])
@login_required
def nueva_categoria():
    name = request.form.get('name', '').strip()
    if not name:
        flash('El nombre de la categoría no puede estar vacío.', 'error')
        return redirect(url_for('faq.index'))
        
    categoria_existente = FAQCategoria.query.filter_by(name=name).first()
    if categoria_existente:
        flash('Esta categoría ya se encuentra registrada.', 'warning')
        return redirect(url_for('faq.index'))
        
    try:
        nueva_cat = FAQCategoria(name=name)
        db.session.add(nueva_cat)
        db.session.commit()
        flash('Categoría creada con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar la categoría: {str(e)}', 'error')
        
    return redirect(url_for('faq.index'))
