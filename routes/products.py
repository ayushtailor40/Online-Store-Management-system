from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.product_service import (
    get_products,
    get_product_by_id,
    create_product,
    update_product,
    delete_product
)
from services.category_service import get_all_categories
from config import Config

products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('')
@products_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    stock_status = request.args.get('stock_status', '').strip()
    sort_by = request.args.get('sort_by', 'name').strip()
    sort_order = request.args.get('sort_order', 'asc').strip()

    categories = get_all_categories(active_only=True)
    result = get_products(
        search=search,
        category_id=category_id,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=Config.ITEMS_PER_PAGE
    )

    return render_template(
        'products/index.html',
        products=result['items'],
        categories=categories,
        pagination=result,
        search=search,
        selected_category=category_id,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_order=sort_order
    )


@products_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    categories = get_all_categories(active_only=True)
    if request.method == 'POST':
        data = {
            'sku': request.form.get('sku'),
            'name': request.form.get('name'),
            'category_id': request.form.get('category_id'),
            'description': request.form.get('description'),
            'cost_price': request.form.get('cost_price'),
            'selling_price': request.form.get('selling_price'),
            'stock_quantity': request.form.get('stock_quantity'),
            'reorder_level': request.form.get('reorder_level'),
            'image_url': request.form.get('image_url'),
            'is_active': 1 if request.form.get('is_active') else 0
        }
        success, message_or_errors, product_id = create_product(data)
        if success:
            flash(message_or_errors, "success")
            return redirect(url_for('products.index'))
        else:
            if isinstance(message_or_errors, list):
                for err in message_or_errors:
                    flash(err, "danger")
            else:
                flash(str(message_or_errors), "danger")

    return render_template('products/form.html', categories=categories, product=None, action_title="Add New Product")


@products_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash("Product not found.", "warning")
        return redirect(url_for('products.index'))

    categories = get_all_categories(active_only=True)

    if request.method == 'POST':
        data = {
            'sku': request.form.get('sku'),
            'name': request.form.get('name'),
            'category_id': request.form.get('category_id'),
            'description': request.form.get('description'),
            'cost_price': request.form.get('cost_price'),
            'selling_price': request.form.get('selling_price'),
            'reorder_level': request.form.get('reorder_level'),
            'image_url': request.form.get('image_url'),
            'is_active': 1 if request.form.get('is_active') else 0
        }
        success, message_or_errors = update_product(product_id, data)
        if success:
            flash(message_or_errors, "success")
            return redirect(url_for('products.index'))
        else:
            if isinstance(message_or_errors, list):
                for err in message_or_errors:
                    flash(err, "danger")
            else:
                flash(str(message_or_errors), "danger")
            product = get_product_by_id(product_id)

    return render_template('products/form.html', categories=categories, product=product, action_title="Edit Product")


@products_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
def delete(product_id):
    success, message = delete_product(product_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('products.index'))
