from flask import Blueprint, render_template, request, flash, jsonify, session, redirect, url_for
from models import db, SystemSettings, User, Product
from auth.routes import login_required, role_required
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import shutil  # Para eliminar archivos de iconos

settings_bp = Blueprint('settings', __name__)

# Configuración para la subida de archivos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico'}
UPLOAD_FOLDER = 'static/images/uploads'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@settings_bp.route('/settings')
@login_required
def settings():
    settings = SystemSettings.get_settings()
    
    # Obtener contadores para la información del sistema (solo para admin)
    users_count = User.query.count() if session.get('role') == 'admin' else 0
    products_count = Product.query.count() if session.get('role') == 'admin' else 0
    
    return render_template('settings.html', 
                         settings=settings,
                         users_count=users_count,
                         products_count=products_count,
                         user_role=session.get('role'))

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
        
        # Manejar la carga del icono
        if 'icon_file' in request.files:
            file = request.files['icon_file']
            if file and file.filename != '' and allowed_file(file.filename):
                # Crear directorio si no existe
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Generar nombre seguro para el archivo
                filename = secure_filename(file.filename)
                # Agregar timestamp para evitar conflictos
                name, ext = os.path.splitext(filename)
                filename = f"icon_{int(datetime.utcnow().timestamp())}{ext}"
                
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Actualizar el nombre del archivo en la base de datos
                settings.icon_filename = f"images/uploads/{filename}"
                flash('Icono actualizado correctamente', 'success')
            elif file and file.filename != '':
                flash('Formato de archivo no permitido', 'danger')
        
        db.session.commit()
        flash('Configuraciones actualizadas correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar configuraciones: {str(e)}', 'danger')
    
    return redirect(url_for('settings.settings'))

@settings_bp.route('/settings/reset_factory', methods=['POST'])
@login_required
@role_required('admin')
def reset_factory_settings():
    try:
        settings = SystemSettings.get_settings()
        
        # Restaurar valores por defecto
        settings.company_name = 'Tradyx'
        settings.currency = '$'
        settings.date_format = 'dd/mm/yyyy'
        settings.language = 'es'
        settings.icon_filename = 'images/icons8-circulacion-de-dinero-100.png'
        
        # Limpiar archivos de iconos subidos (opcional)
        try:
            # Eliminar todos los archivos en la carpeta de uploads
            if os.path.exists(UPLOAD_FOLDER):
                for filename in os.listdir(UPLOAD_FOLDER):
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.isfile(file_path) and filename.startswith('icon_'):
                        os.remove(file_path)
        except Exception as e:
            print(f"Error al limpiar archivos de iconos: {e}")
        
        db.session.commit()
        flash('Configuración restaurada a valores de fábrica correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al restaurar configuración: {str(e)}', 'danger')
    
    return redirect(url_for('settings.settings'))

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