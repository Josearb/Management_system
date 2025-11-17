from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file
from models import db, CashRegister, User, get_system_settings
from auth.routes import login_required
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

cash_register_bp = Blueprint('cash_register', __name__)

@cash_register_bp.route('/cash_register', methods=['GET', 'POST'])
@login_required
def cash_register():
    if request.method == 'POST':
        try:
            transfer_amount = float(request.form.get('transfer_amount', 0))
            cash_amount = float(request.form.get('cash_amount', 0))
            
            new_register = CashRegister(
                transfer_amount=transfer_amount,
                cash_amount=cash_amount,
                user_id=session['user_id']
            )
            new_register.calculate_total()
            
            db.session.add(new_register)
            db.session.commit()
            flash('Registro de caja guardado exitosamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar registro: {str(e)}', 'danger')
        
        return redirect(url_for('cash_register.cash_register'))
    
    # GET request - mostrar todos los registros (NO solo los de hoy)
    all_records = CashRegister.query.order_by(CashRegister.date.desc()).all()
    
    return render_template('cash_register.html', 
                         today_records=all_records)  # Cambiado el nombre para claridad

@cash_register_bp.route('/cash_register/report')
@login_required
def print_cash_register_report():
    # Obtener TODOS los registros, no solo los del día actual
    records = CashRegister.query.order_by(CashRegister.date.desc()).all()
    
    # Calcular totales
    total_transfer = sum(record.transfer_amount for record in records)
    total_cash = sum(record.cash_amount for record in records)
    grand_total = total_transfer + total_cash
    
    return render_template('cash_register_report.html',
                         records=records,
                         total_transfer=total_transfer,
                         total_cash=total_cash,
                         grand_total=grand_total,
                         date=datetime.now().strftime("%d/%m/%Y"))

@cash_register_bp.route('/cash_register/report/pdf')
@login_required
def download_cash_register_pdf():
    # Obtener TODOS los registros, no solo los del día actual
    records = CashRegister.query.order_by(CashRegister.date.desc()).all()
    
    # Calcular totales
    total_transfer = sum(record.transfer_amount for record in records)
    total_cash = sum(record.cash_amount for record in records)
    grand_total = total_transfer + total_cash
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
    elements.append(Paragraph(f"Reporte de Caja - {current_date}", styles['Heading2']))
    elements.append(Paragraph(" ", styles['Normal']))
    
    # Si no hay registros, mostrar mensaje
    if not records:
        elements.append(Paragraph("No hay registros de caja disponibles.", styles['Normal']))
    else:
        # Datos de la tabla
        data = [["#", "Fecha", "Hora", "Transferencia", "Efectivo", "Total", "Usuario"]]
        
        for idx, record in enumerate(records, 1):
            data.append([
                str(idx),
                record.date.strftime("%d/%m/%Y"),
                record.date.strftime("%H:%M"),
                f"${record.transfer_amount:.2f}",
                f"${record.cash_amount:.2f}",
                f"${record.total_amount:.2f}",
                record.user.username
            ])
        
        # Crear tabla
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        # Totales
        elements.append(Paragraph(" ", styles['Normal']))
        elements.append(Paragraph(f"Total Transferencia: ${total_transfer:.2f}", styles['Normal']))
        elements.append(Paragraph(f"Total Efectivo: ${total_cash:.2f}", styles['Normal']))
        elements.append(Paragraph(f"Total General: ${grand_total:.2f}", styles['Heading3']))
    
    # Generar PDF
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"reporte_caja_completo_{current_date.replace('/', '-')}.pdf",
        mimetype='application/pdf'
    )

@cash_register_bp.route('/cash_register/delete/<int:register_id>')
@login_required
def delete_cash_register(register_id):
    try:
        register = CashRegister.query.get_or_404(register_id)
        db.session.delete(register)
        db.session.commit()
        flash('Registro de caja eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar registro: {str(e)}', 'danger')
    return redirect(url_for('cash_register.cash_register'))