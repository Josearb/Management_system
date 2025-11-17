# -*- coding: utf-8 -*-
from flask import Flask, render_template, session
import os
from models import db, init_db
from auth.routes import auth_bp, login_required
from sales.routes import sales_bp
from inventory.routes import inventory_bp
from crm.routes import crm_bp
from maintenance.routes import maintenance_bp
from users.routes import users_bp
from cash_register.routes import cash_register_bp
from settings.routes import settings_bp
from analytics import analytics_bp

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_12345'

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(crm_bp)
app.register_blueprint(maintenance_bp)
app.register_blueprint(users_bp)
app.register_blueprint(cash_register_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(analytics_bp, url_prefix='/analytics')

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'erp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)
with app.app_context():
    init_db(app)

# Context Processor para hacer disponibles los settings en todas las plantillas
@app.context_processor
def inject_settings():
    from models import SystemSettings
    try:
        settings = SystemSettings.get_settings()
        return dict(settings=settings)
    except:
        # Si hay algún error (tabla no existe, etc.), retornar valores por defecto
        return dict(settings=None)

# Función para obtener settings en las rutas
def get_system_settings():
    from models import SystemSettings
    try:
        return SystemSettings.get_settings()
    except:
        return None

@app.route('/')
@login_required
def dashboard():
    modules = []
    
    if session['role'] == 'admin':
        modules = [
            {'name': 'Ventas', 'icon': 'images/sales_icon.png', 'description': 'Gestión de pedidos y facturas', 'route': 'sales.sales'},
            {'name': 'Inventario', 'icon': 'images/inventory_icon.png', 'description': 'Gestión de productos y stock', 'route': 'inventory.inventory'},
            {'name': 'CRM', 'icon': 'images/crm_icon.png', 'description': 'Gestión de clientes y contactos', 'route': 'crm.crm'},
            {'name': 'Mantenimiento', 'icon': 'images/maintenance.png', 'description': 'Gestión de tareas de mantenimiento', 'route': 'maintenance.maintenance'},
            {'name': 'Usuarios', 'icon': 'images/users.png', 'description': 'Gestión de usuarios del sistema', 'route': 'users.users'},
            {'name': 'Administrar Ventas', 'icon': 'images/icons8-analítica-100.png', 'description': 'Estadísticas de ventas', 'route': 'analytics.dashboard'},
            {'name': 'Registro de Caja', 'icon': 'images/icons8-cajero-automático-100.png', 'description': 'Control de transferencias y efectivo', 'route': 'cash_register.cash_register'},
            {'name': 'Ajustes', 'icon': 'images/icons8-ajustes-100.png', 'description': 'Configuración del sistema', 'route': 'settings.settings'}
        ]
    else:
        modules = [
            {'name': 'Ventas', 'icon': 'images/sales_icon.png', 'description': 'Registro de ventas del día', 'route': 'sales.sales'},
            {'name': 'Inventario', 'icon': 'images/inventory_icon.png', 'description': 'Consulta de productos', 'route': 'inventory.inventory'},
            {'name': 'Ajustes', 'icon': 'images/icons8-ajustes-100.png', 'description': 'Configuración del sistema', 'route': 'settings.settings'}
        ]
    
    return render_template('dashboard.html', modules=modules)

if __name__ == '__main__':
    app.run(debug=True)