from flask import Blueprint, render_template, request, jsonify
from routes.auth import login_required
from services.analytics_service import (
    get_comprehensive_analytics,
    get_monthly_sales_trend,
    get_revenue_by_category,
    get_top_selling_products,
    get_profit_by_product,
    get_order_status_distribution
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('')
@analytics_bp.route('/')
@login_required
def index():
    preset = request.args.get('preset', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    analytics_data = get_comprehensive_analytics(
        preset=preset,
        start_date=start_date,
        end_date=end_date
    )

    return render_template(
        'analytics/index.html',
        analytics=analytics_data,
        preset=preset,
        start_date=start_date,
        end_date=end_date
    )


@analytics_bp.route('/api/charts')
@login_required
def api_charts():
    """Returns Chart.js data packages for the analytics page."""
    monthly_trend = get_monthly_sales_trend(months_limit=12)
    cat_revenue = get_revenue_by_category()
    top_products = get_top_selling_products(limit=10)
    profit_products = get_profit_by_product(limit=10)
    status_dist = get_order_status_distribution()

    return jsonify({
        'monthly_trend': monthly_trend,
        'category_revenue': cat_revenue,
        'top_products': top_products,
        'profit_products': profit_products,
        'status_dist': status_dist
    })
