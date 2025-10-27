from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, Customer
from auth.routes import login_required, role_required

crm_bp = Blueprint('crm', __name__)

@crm_bp.route('/crm', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crm():
    if request.method == 'POST':
        try:
            new_customer = Customer(
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form['phone']
            )
            db.session.add(new_customer)
            db.session.commit()
            flash('Cliente agregado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar cliente: {str(e)}', 'danger')
        return redirect(url_for('crm.crm'))
    
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('crm.html', customers=customers)

@crm_bp.route('/crm/update/<int:customer_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        customer.name = request.form['name']
        customer.email = request.form['email']
        customer.phone = request.form['phone']
        db.session.commit()
        flash('Cliente actualizado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar cliente: {str(e)}', 'danger')
    return redirect(url_for('crm.crm'))

@crm_bp.route('/crm/delete/<int:customer_id>')
@login_required
@role_required('admin')
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Cliente eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cliente: {str(e)}', 'danger')
    return redirect(url_for('crm.crm'))