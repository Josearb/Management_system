from flask import Blueprint, render_template, request, flash, session, jsonify, send_file, redirect, url_for
from models import db, Sale, Product, User, DailySales, get_system_settings
from datetime import datetime
from auth.routes import login_required, role_required
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id')
            quantity = int(request.form.get('quantity', 0))
            
            if not product_id or quantity <= 0:
                flash('Debe ingresar una cantidad válida', 'danger')
                return redirect(url_for('sales.sales'))

            product = Product.query.get_or_404(product_id)
            
            if product.quantity < quantity:
                flash(f'Stock insuficiente de {product.name}. Disponible: {product.quantity}', 'danger')
                return redirect(url_for('sales.sales'))

            new_sale = Sale(
                customer="Cliente ocasional",
                total=product.price * quantity,
                date=datetime.utcnow(),
                user_id=session['user_id'],
                product_id=product.id,
                quantity=quantity
            )
            
            product.quantity -= quantity
            product.daily_sales += quantity
            
            db.session.add(new_sale)
            db.session.commit()
            flash('Venta registrada exitosamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar venta: {str(e)}', 'danger')
        
        return redirect(url_for('sales.sales'))
    
    # GET request
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Filtrar productos por nombre (búsqueda case-insensitive)
        products = Product.query.filter(
            Product.name.ilike(f'%{search_query}%')
        ).order_by(Product.name).all()
    else:
        products = Product.query.order_by(Product.name).all()
    
    # Obtener actividades para el chatter
    chatter_activities = db.session.query(
        Sale, User, Product
    ).join(
        User, User.id == Sale.user_id
    ).join(
        Product, Product.id == Sale.product_id
    ).order_by(
        Sale.date.desc()
    ).limit(50).all()
    
    # Calcular total acumulado del turno
    today_total = db.session.query(db.func.sum(Sale.total)).filter(
        db.func.date(Sale.date) == datetime.utcnow().date()
    ).scalar() or 0
    
    return render_template('modules/sales/sales.html', 
                         products=products,
                         chatter_activities=chatter_activities,
                         current_date=datetime.utcnow().date(),
                         today_total=today_total,
                         search_query=search_query,
                         show_cash_register=True)  

@sales_bp.route('/api/sales', methods=['POST'])
@login_required
def api_create_sale():
    try:
        sales_data = request.get_json()
        customer = sales_data.get('customer', 'Cliente ocasional')
        items = sales_data['items']
        
        if not items:
            return jsonify({'success': False, 'message': 'No items selected'})
        
        # Process each item in the sale
        for item in items:
            product = Product.query.get(item['product_id'])
            quantity = int(item['quantity'])
            
            if quantity <= 0:
                continue
            
            if product.quantity < quantity:
                return jsonify({
                    'success': False,
                    'message': f'Insufficient stock for {product.name}. Available: {product.quantity}'
                })
            
            # Update inventory
            product.quantity -= quantity
            product.daily_sales += quantity
            
            # Record sale
            new_sale = Sale(
                customer="Cliente ocasional",
                total=product.price * quantity,
                date=datetime.utcnow(), 
                user_id=session['user_id'],
                product_id=product.id,
                quantity=quantity
            )
            db.session.add(new_sale)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Sale recorded successfully',
            'new_stock': {product.id: product.quantity for product in Product.query.all()}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@sales_bp.route('/api/sales/<int:sale_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_sale(sale_id):
    try:
        sale = Sale.query.get_or_404(sale_id)
        product = Product.query.get(sale.product_id)
        
        # Restore inventory
        product.quantity += sale.quantity
        product.daily_sales -= sale.quantity
        
        db.session.delete(sale)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sale deleted and inventory restored',
            'new_stock': product.quantity
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@sales_bp.route('/sales/reset', methods=['POST'])
@login_required
def reset_daily_sales():
    try:
        today = datetime.utcnow().date()
        
        # Calcular total del día antes de eliminar
        today_total = db.session.query(db.func.sum(Sale.total)).filter(
            db.func.date(Sale.date) == today
        ).scalar() or 0

        # Crear registro histórico
        if today_total > 0:
            new_daily_record = DailySales(
                date=today.strftime("%Y-%m-%d"),  # Convertir a string
                total=today_total,
                user_id=session['user_id']
            )
            db.session.add(new_daily_record)

        # SOLUCIÓN: Eliminar ventas del día usando synchronize_session=False
        db.session.query(Sale).filter(
            db.func.date(Sale.date) == today
        ).delete(synchronize_session=False)

        # Resetear contadores diarios
        for product in Product.query.all():
            product.daily_sales = 0

        db.session.commit()

        flash('✅ Contadores y ventas del día reiniciados correctamente. Total registrado: $%.2f' % today_total, 'success')
        return jsonify({
            'success': True,
            'message': 'Contadores y ventas del día reiniciados. Total registrado: $%.2f' % today_total
        })

    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al reiniciar contadores: {str(e)}', 'danger')
        return jsonify({
            'success': False,
            'message': f'Error al reiniciar: {str(e)}'
        }), 500

@sales_bp.route('/sales/report')
@login_required
def print_daily_report():
    # Get products sold today (daily_sales > 0)
    products_sold = Product.query.filter(Product.daily_sales > 0).all()
    total_sales = sum(p.price * p.daily_sales for p in products_sold)
    
    return render_template('reports/sales/sales_report.html',
                        products=products_sold,
                        total=total_sales,
                        date=datetime.now().strftime("%d/%m/%Y"))

@sales_bp.route('/sales/report/pdf')
@login_required
def download_sales_pdf():
    # Obtener productos vendidos hoy
    products_sold = Product.query.filter(Product.daily_sales > 0).all()
    total_sales = sum(p.price * p.daily_sales for p in products_sold)
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    # Obtener configuración de la empresa
    settings = get_system_settings()
    company_name = settings.company_name if settings else "Tradyx"
    
    # Crear buffer para el PDF
    buffer = BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Contenido del PDF
    elements = []
    
    # Título con nombre de la empresa
    elements.append(Paragraph(f"{company_name}", styles['Title']))
    elements.append(Paragraph(f"Reporte de Ventas - {current_date}", styles['Heading2']))
    elements.append(Paragraph(" ", styles['Normal']))  # Espacio
    
    # Datos de la tabla
    data = [["#", "Producto", "Cantidad", "Precio Unit.", "Subtotal"]]
    
    for idx, product in enumerate(products_sold, 1):
        data.append([
            str(idx),
            product.name,
            str(product.daily_sales),
            f"${product.price:.2f}",
            f"${product.price * product.daily_sales:.2f}"
        ])
    
    # Total
    data.append(["", "", "", "Total:", f"${total_sales:.2f}"])
    
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
    ]))
    
    elements.append(table)
    
    # Generar PDF
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"reporte_ventas_{current_date.replace('/', '-')}.pdf",
        mimetype='application/pdf'
    )