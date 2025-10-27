from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, session
from models import db, Product, Sale
from auth.routes import login_required, role_required
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    if request.method == 'POST' and session['role'] == 'admin':
        try:
            new_product = Product(
                name=request.form['name'],
                quantity=int(request.form['quantity']),
                price=float(request.form['price']),
                daily_sales=0,
                unit_measure=request.form['unit_measure']  
            )
            db.session.add(new_product)
            db.session.commit()
            flash('Producto agregado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar producto: {str(e)}', 'danger')
        return redirect(url_for('inventory.inventory'))
    
    products = Product.query.order_by(Product.name).all()
    return render_template('inventory.html', products=products)

@inventory_bp.route('/inventory/delete/<int:product_id>')
@login_required
@role_required('admin')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        # Eliminar primero las ventas asociadas
        Sale.query.filter_by(product_id=product_id).delete()
        # Luego eliminar el producto
        db.session.delete(product)
        db.session.commit()
        flash('Producto y sus ventas asociadas eliminados correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar producto: {str(e)}', 'danger')
    return redirect(url_for('inventory.inventory'))

@inventory_bp.route('/inventory/update/<int:product_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        product.name = request.form['name']
        product.quantity = int(request.form['quantity'])
        product.price = float(request.form['price'])
        product.unit_measure = request.form['unit_measure']  
        db.session.commit()
        flash('Producto actualizado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar producto: {str(e)}', 'danger')
    return redirect(url_for('inventory.inventory'))

@inventory_bp.route('/inventory/report')
@login_required
def print_inventory_report():
    # Obtener todos los productos del inventario
    products = Product.query.order_by(Product.name).all()
    
    # Calcular totales
    total_products = sum(product.quantity for product in products)
    total_value = sum(product.price * product.quantity for product in products)
    
    return render_template('inventory_report.html',
                        products=products,
                        total_products=total_products,
                        total_value=total_value,
                        date=datetime.now().strftime("%d/%m/%Y"))

@inventory_bp.route('/inventory/report/pdf')
@login_required
def download_inventory_pdf():
    # Obtener todos los productos del inventario
    products = Product.query.order_by(Product.name).all()
    
    # Calcular totales
    total_products = sum(product.quantity for product in products)
    total_value = sum(product.price * product.quantity for product in products)
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    # Crear buffer para el PDF
    buffer = BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Contenido del PDF
    elements = []
    
    # Título
    elements.append(Paragraph(f"Reporte de Inventario - {current_date}", styles['Title']))
    elements.append(Paragraph("Tradyx", styles['Normal']))
    elements.append(Paragraph(" ", styles['Normal']))  # Espacio
    
    # Datos de la tabla - AGREGADA COLUMNA UNIDAD DE MEDIDA
    data = [["#", "Producto", "Cantidad", "Unidad", "Precio Unit.", "Valor Total"]]
    
    for idx, product in enumerate(products, 1):
        data.append([
            str(idx),
            product.name,
            str(product.quantity),
            product.unit_measure,  # Nueva columna
            f"${product.price:.2f}",
            f"${product.price * product.quantity:.2f}"
        ])
    
    # Totales
    data.append(["", "TOTAL PRODUCTOS:", str(total_products), "", "VALOR TOTAL:", f"${total_value:.2f}"])
    
    # Crear tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-2, -1), colors.lightgrey),
        ('BACKGROUND', (-1, -1), (-1, -1), colors.grey),
        ('TEXTCOLOR', (-1, -1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(table)
    
    # Generar PDF
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"reporte_inventario_{current_date.replace('/', '-')}.pdf",
        mimetype='application/pdf'
    )