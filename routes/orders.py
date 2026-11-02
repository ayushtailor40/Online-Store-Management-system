from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required
from services.order_service import (
    get_orders,
    get_order_by_id,
    create_order,
    update_order_status
)
from services.customer_service import get_customers
from services.product_service import get_products
from config import Config

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


@orders_bp.route('')
@orders_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    payment_status = request.args.get('payment_status', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    result = get_orders(
        search=search,
        status=status,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=Config.ITEMS_PER_PAGE
    )

    return render_template(
        'orders/index.html',
        orders=result['items'],
        pagination=result,
        search=search,
        status=status,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date
    )


@orders_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        payment_method = request.form.get('payment_method', 'Credit Card')
        notes = request.form.get('notes', '')

        # Parse dynamic item lists sent from form
        # We accept either list form inputs: product_id[], quantity[]
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        items = []
        for pid, qty in zip(product_ids, quantities):
            if pid and qty:
                try:
                    items.append({'product_id': int(pid), 'quantity': int(qty)})
                except ValueError:
                    continue

        try:
            order_id, order_number = create_order(
                customer_id=customer_id,
                items=items,
                payment_method=payment_method,
                notes=notes
            )
            flash(f"Order {order_number} created successfully!", "success")
            return redirect(url_for('orders.details', order_id=order_id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")

    # For rendering form, load all customers and active products with stock > 0
    customers_res = get_customers(per_page=200)['items']
    products_res = get_products(per_page=200, include_inactive=False)['items']

    return render_template(
        'orders/form.html',
        customers=customers_res,
        products=products_res
    )


@orders_bp.route('/<int:order_id>')
@login_required
def details(order_id):
    order = get_order_by_id(order_id)
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for('orders.index'))

    return render_template('orders/details.html', order=order)


@orders_bp.route('/<int:order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    new_status = request.form.get('status')
    success, message = update_order_status(order_id, new_status)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('orders.details', order_id=order_id))


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel(order_id):
    success, message = update_order_status(order_id, 'Cancelled')
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('orders.details', order_id=order_id))
