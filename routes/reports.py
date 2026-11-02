from datetime import datetime
from flask import Blueprint, render_template, request, Response
from routes.auth import login_required
from services.report_service import (
    generate_sales_report_csv,
    generate_product_performance_csv,
    generate_customer_report_csv,
    generate_inventory_report_csv
)
from services.category_service import get_all_categories

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('')
@reports_bp.route('/')
@login_required
def index():
    categories = get_all_categories(active_only=True)
    return render_template('reports/index.html', categories=categories)


@reports_bp.route('/export/sales')
@login_required
def export_sales():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')

    csv_data = generate_sales_report_csv(start_date=start_date, end_date=end_date, status=status)
    filename = f"sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route('/export/products')
@login_required
def export_products():
    category_id = request.args.get('category_id', type=int)
    csv_data = generate_product_performance_csv(category_id=category_id)
    filename = f"product_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route('/export/customers')
@login_required
def export_customers():
    csv_data = generate_customer_report_csv()
    filename = f"customers_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route('/export/inventory')
@login_required
def export_inventory():
    status = request.args.get('status')  # None, 'low_stock', 'out_of_stock'
    csv_data = generate_inventory_report_csv(status_filter=status)
    prefix = "low_stock_report" if status == 'low_stock' else "inventory_report"
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
