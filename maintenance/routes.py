from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, MaintenanceTask
from auth.routes import login_required, role_required

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/maintenance', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def maintenance():
    if request.method == 'POST':
        try:
            new_task = MaintenanceTask(
                equipment=request.form['equipment'],
                description=request.form['description'],
                priority=request.form['priority'],
                assigned_to=request.form['assigned_to'],
                due_date=request.form['due_date']
            )
            db.session.add(new_task)
            db.session.commit()
            flash('Tarea de mantenimiento creada exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear tarea: {str(e)}', 'danger')
        return redirect(url_for('maintenance.maintenance'))
    
    tasks = MaintenanceTask.query.order_by(MaintenanceTask.priority, MaintenanceTask.due_date).all()
    return render_template('maintenance.html', tasks=tasks)

@maintenance_bp.route('/maintenance/update/<int:task_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    try:
        task.equipment = request.form['equipment']
        task.description = request.form['description']
        task.priority = request.form['priority']
        task.status = request.form['status']
        task.assigned_to = request.form['assigned_to']
        task.due_date = request.form['due_date']
        db.session.commit()
        flash('Tarea actualizada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar tarea: {str(e)}', 'danger')
    return redirect(url_for('maintenance.maintenance'))

@maintenance_bp.route('/maintenance/complete/<int:task_id>')
@login_required
@role_required('admin')
def complete_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    try:
        task.status = 'Completado'
        db.session.commit()
        flash('Tarea marcada como completada', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al completar tarea: {str(e)}', 'danger')
    return redirect(url_for('maintenance.maintenance'))

@maintenance_bp.route('/maintenance/delete/<int:task_id>')
@login_required
@role_required('admin')
def delete_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    try:
        db.session.delete(task)
        db.session.commit()
        flash('Tarea eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar tarea: {str(e)}', 'danger')
    return redirect(url_for('maintenance.maintenance'))