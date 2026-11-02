import os
import secrets
import logging
from datetime import datetime
from flask import Flask, render_template, session, request, abort, g
from config import Config
from database.db import close_db, query_db
from routes import (
    auth_bp,
    dashboard_bp,
    products_bp,
    categories_bp,
    customers_bp,
    orders_bp,
    inventory_bp,
    analytics_bp,
    reports_bp
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Teardown database connections after request
    app.teardown_appcontext(close_db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)

    # CSRF Protection mechanism
    @app.before_request
    def check_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(24)

        if app.config.get('TESTING'):
            return

        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            # Allow JSON API or check form / header
            token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
            expected = session.get('csrf_token')
            if not token or token != expected:
                logger.warning(f"CSRF validation failed for endpoint: {request.path}")
                abort(400, description="Invalid or missing CSRF token. Please refresh and try again.")

    # Context processor to inject global variables into templates
    @app.context_processor
    def inject_global_data():
        def get_csrf_token():
            return session.get('csrf_token', '')

        # Low stock notification count
        low_stock_count = 0
        try:
            res = query_db("SELECT COUNT(*) AS cnt FROM products WHERE is_active = 1 AND stock_quantity <= reorder_level", one=True)
            if res:
                low_stock_count = res['cnt']
        except Exception:
            low_stock_count = 0

        return {
            'csrf_token': get_csrf_token,
            'low_stock_notification_count': low_stock_count,
            'current_year': datetime.now().year,
            'admin_user': {
                'id': session.get('admin_id'),
                'name': session.get('admin_name', 'Admin'),
                'username': session.get('admin_username', 'admin'),
                'role': session.get('admin_role', 'Administrator')
            } if 'admin_id' in session else None
        }

    # Custom Jinja filters for formatting
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter('datetime_format')
    def datetime_format_filter(value):
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                # Try parsing ISO or MySQL format
                dt = datetime.fromisoformat(value.replace('Z', ''))
                return dt.strftime('%b %d, %Y %I:%M %p')
            except Exception:
                return value
        elif isinstance(value, datetime):
            return value.strftime('%b %d, %Y %I:%M %p')
        return str(value)

    @app.template_filter('date_format')
    def date_format_filter(value):
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', ''))
                return dt.strftime('%b %d, %Y')
            except Exception:
                return value[:10]
        elif isinstance(value, datetime):
            return value.strftime('%b %d, %Y')
        return str(value)

    # Custom Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template('base.html', error_title="400 - Bad Request", error_message=str(e)), 400

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('base.html', error_title="404 - Page Not Found", error_message="The requested resource or page does not exist."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal Server Error: {str(e)}", exc_info=True)
        return render_template('base.html', error_title="500 - Server Error", error_message="An internal server error occurred. Please contact the administrator."), 500

    return app


app = create_app()

if __name__ == '__main__':
    # Local development server
    port = int(os.getenv('PORT', 5000))
    print(f"Starting Smart Online Store Management System on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)
