from flask import Blueprint, render_template, request, flash, redirect, url_for, session
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
    
    users = User.query.order_by(User.role, User.username).all()
    return render_template('users.html', users=users)

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