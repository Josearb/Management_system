from flask import Blueprint, render_template, request, flash, jsonify, session, redirect, url_for
from models import db, SystemSettings, User, Product
from auth.routes import login_required, role_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def settings():
    settings = SystemSettings.get_settings()
    
    # Obtener contadores para la información del sistema
    users_count = User.query.count()
    products_count = Product.query.count()
    
    return render_template('settings.html', 
                         settings=settings,
                         users_count=users_count,
                         products_count=products_count)

@settings_bp.route('/settings/update', methods=['POST'])
@login_required
@role_required('admin')
def update_settings():
    try:
        settings = SystemSettings.get_settings()
        
        # Configuraciones generales
        settings.company_name = request.form.get('company_name', 'Tradyx')
        settings.currency = request.form.get('currency', '$')
        settings.date_format = request.form.get('date_format', 'dd/mm/yyyy')
        settings.language = request.form.get('language', 'es')
        
        db.session.commit()
        flash('Configuraciones actualizadas correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar configuraciones: {str(e)}', 'danger')
    
    return redirect(url_for('settings.settings'))

@settings_bp.route('/settings/toggle_dark_mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    try:
        dark_mode = request.json.get('dark_mode', False)
        session['dark_mode'] = dark_mode
        
        # Si es admin, guardar en base de datos para todos los usuarios
        if session.get('role') == 'admin':
            settings = SystemSettings.get_settings()
            settings.dark_mode = dark_mode
            db.session.commit()
        
        return jsonify({'success': True, 'dark_mode': dark_mode})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        user = User.query.get(session['user_id'])
        
        if not user.check_password(current_password):
            flash('La contraseña actual es incorrecta', 'danger')
            return redirect(url_for('settings.settings'))
        
        if new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden', 'danger')
            return redirect(url_for('settings.settings'))
        
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('settings.settings'))
        
        user.set_password(new_password)
        db.session.commit()
        
        flash('Contraseña actualizada correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar contraseña: {str(e)}', 'danger')
    
    return redirect(url_for('settings.settings'))