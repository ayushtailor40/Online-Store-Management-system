# Routes package
from .auth import auth_bp
from .dashboard import dashboard_bp
from .products import products_bp
from .categories import categories_bp
from .customers import customers_bp
from .orders import orders_bp
from .inventory import inventory_bp
from .analytics import analytics_bp
from .reports import reports_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'products_bp',
    'categories_bp',
    'customers_bp',
    'orders_bp',
    'inventory_bp',
    'analytics_bp',
    'reports_bp'
]
