from flask import Blueprint, render_template, request, jsonify
from routes.auth import login_required
from services.analytics_service import (
    get_dashboard_kpis,
    get_monthly_sales_trend,
    get_revenue_by_category,
    get_top_selling_products,
    get_profit_by_product,
    get_order_status_distribution,
    parse_date_range
)
from services.category_service import get_all_categories
from services.order_service import get_orders
from services.product_service import get_low_stock_products

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Main Dashboard View."""
    categories = get_all_categories(active_only=True)
    recent_orders = get_orders(page=1, per_page=7)['items']
    low_stock = get_low_stock_products(limit=5)
    best_seller = get_top_selling_products(limit=1)['items']
    top_product = best_seller[0] if best_seller else None

    # Initial KPI load for all time
    kpis = get_dashboard_kpis()

    return render_template(
        'dashboard.html',
        categories=categories,
        recent_orders=recent_orders,
        low_stock=low_stock,
        top_product=top_product,
        kpis=kpis
    )


@dashboard_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """
    JSON API for dynamic KPI and Chart.js updates based on active filters:
    - preset: 'all', 'today', '7d', '30d', '90d', 'ytd', '1y'
    - start_date, end_date (if preset='custom')
    - category_id
    """
    preset = request.args.get('preset', 'all')
    custom_start = request.args.get('start_date')
    custom_end = request.args.get('end_date')
    category_id = request.args.get('category_id')
    if category_id in ('all', '', None):
        category_id = None
    else:
        try:
            category_id = int(category_id)
        except ValueError:
            category_id = None

    start, end = parse_date_range(preset, custom_start, custom_end)

    kpis = get_dashboard_kpis(start_date=start, end_date=end, category_id=category_id)
    monthly_trend = get_monthly_sales_trend(months_limit=12)
    cat_revenue = get_revenue_by_category()
    top_products = get_top_selling_products(limit=10)
    profit_products = get_profit_by_product(limit=10)
    status_distribution = get_order_status_distribution()

    return jsonify({
        'kpis': kpis,
        'charts': {
            'monthly_trend': monthly_trend,
            'category_revenue': cat_revenue,
            'top_products': top_products,
            'profit_products': profit_products,
            'status_distribution': status_distribution
        }
    })
