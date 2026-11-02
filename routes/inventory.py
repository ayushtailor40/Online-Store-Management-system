from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.inventory_service import (
    get_inventory_status,
    adjust_stock,
    get_inventory_movements
)
from services.category_service import get_all_categories
from config import Config

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('')
@inventory_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    status_filter = request.args.get('status', '').strip()

    categories = get_all_categories(active_only=True)
    inventory_data = get_inventory_status(
        search=search,
        category_id=category_id,
        status_filter=status_filter,
        page=page,
        per_page=Config.ITEMS_PER_PAGE
    )
    recent_movements = get_inventory_movements(limit=15)

    return render_template(
        'inventory/index.html',
        items=inventory_data['items'],
        summary=inventory_data['summary'],
        pagination=inventory_data,
        categories=categories,
        movements=recent_movements,
        search=search,
        selected_category=category_id,
        selected_status=status_filter
    )


@inventory_bp.route('/adjust', methods=['POST'])
@login_required
def adjust():
    product_id = request.form.get('product_id', type=int)
    adjustment_type = request.form.get('adjustment_type')  # 'ADD' or 'REMOVE'
    quantity = request.form.get('quantity')
    reason = request.form.get('reason')

    success, message = adjust_stock(
        product_id=product_id,
        adjustment_type=adjustment_type,
        quantity=quantity,
        reason=reason
    )
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for('inventory.index'))
