from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import Usuario

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está autenticado, redirigir al dashboard
    if current_user.is_authenticated:
        return redirect(url_for('homologaciones.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = Usuario.query.filter_by(username=username).first()
        
        # Validaciones de seguridad básicas
        if not user or not user.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'error')
            return render_template('auth/login.html')
            
        if not user.active:
            flash('Tu cuenta se encuentra inactiva. Contacta al Administrador.', 'error')
            return render_template('auth/login.html')
            
        login_user(user, remember=remember)
        flash(f'¡Bienvenido de nuevo, {user.username}!', 'success')
        
        # Redirigir a la página a la que intentaba acceder
        next_page = request.args.get('next')
        return redirect(next_page or url_for('homologaciones.dashboard'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('auth.cambiar_password'))
            
        if not current_user.check_password(current_password):
            flash('La contraseña actual es incorrecta.', 'error')
            return redirect(url_for('auth.cambiar_password'))
            
        if new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'error')
            return redirect(url_for('auth.cambiar_password'))
            
        if len(new_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('auth.cambiar_password'))
            
        current_user.set_password(new_password)
        from extensions import db
        db.session.commit()
        
        flash('Tu contraseña ha sido actualizada con éxito.', 'success')
        return redirect(url_for('homologaciones.dashboard'))
        
    return render_template('auth/cambiar_password.html')
