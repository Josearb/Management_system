from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from models import db, User, Sale
from auth.routes import login_required, role_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def users():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
        else:
            try:
                new_user = User(username=username, role=role)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Usuario creado exitosamente', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear usuario: {str(e)}', 'danger')
        return redirect(url_for('users.users'))
    
    # Obtener parámetro de búsqueda
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Filtrar usuarios por nombre de usuario o rol (búsqueda case-insensitive)
        users = User.query.filter(
            User.username.ilike(f'%{search_query}%') |
            User.role.ilike(f'%{search_query}%')
        ).order_by(User.role, User.username).all()
    else:
        users = User.query.order_by(User.role, User.username).all()
    
    # Organizar usuarios por rol para la vista tree
    users_by_role = {}
    for user in users:
        if user.role not in users_by_role:
            users_by_role[user.role] = []
        users_by_role[user.role].append(user)
    
    return render_template('modules/users/users.html', 
                         users=users,
                         users_by_role=users_by_role,
                         search_query=search_query)

@users_bp.route('/users/delete/<int:user_id>')
@login_required
@role_required('admin')
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('No puedes eliminarte a ti mismo', 'danger')
    else:
        user = User.query.get_or_404(user_id)
        try:
            Sale.query.filter_by(user_id=user_id).delete()
            db.session.delete(user)
            db.session.commit()
            flash('Usuario eliminado correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    return redirect(url_for('users.users'))

@users_bp.route('/users/toggle_status/<int:user_id>')
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'No puedes modificar tu propio estado'})
    
    user = User.query.get_or_404(user_id)
    try:
        # Aquí puedes agregar lógica para cambiar estado si agregas ese campo
        # Por ahora solo confirmamos que el usuario existe
        db.session.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})