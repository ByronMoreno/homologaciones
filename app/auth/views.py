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
