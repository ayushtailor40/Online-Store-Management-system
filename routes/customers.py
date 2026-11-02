from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.customer_service import (
    get_customers,
    get_customer_by_id,
    get_customer_orders,
    create_customer,
    update_customer,
    get_top_spending_customers
)
from config import Config

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('')
@customers_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'name').strip()
    sort_order = request.args.get('sort_order', 'asc').strip()

    result = get_customers(
        search=search,
        page=page,
        per_page=Config.ITEMS_PER_PAGE,
        sort_by=sort_by,
        sort_order=sort_order
    )
    top_spenders = get_top_spending_customers(limit=3)

    return render_template(
        'customers/index.html',
        customers=result['items'],
        pagination=result,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        top_spenders=top_spenders
    )


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'postal_code': request.form.get('postal_code')
        }
        success, message_or_errors, cust_id = create_customer(data)
        if success:
            flash(message_or_errors, "success")
            return redirect(url_for('customers.details', customer_id=cust_id))
        else:
            if isinstance(message_or_errors, list):
                for err in message_or_errors:
                    flash(err, "danger")
            else:
                flash(str(message_or_errors), "danger")

    return render_template('customers/form.html', customer=None, action_title="Add New Customer")


@customers_bp.route('/<int:customer_id>')
@login_required
def details(customer_id):
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for('customers.index'))

    orders = get_customer_orders(customer_id)
    return render_template('customers/details.html', customer=customer, orders=orders)


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    customer = get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for('customers.index'))

    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'postal_code': request.form.get('postal_code')
        }
        success, message_or_errors = update_customer(customer_id, data)
        if success:
            flash(message_or_errors, "success")
            return redirect(url_for('customers.details', customer_id=customer_id))
        else:
            if isinstance(message_or_errors, list):
                for err in message_or_errors:
                    flash(err, "danger")
            else:
                flash(str(message_or_errors), "danger")
            customer = get_customer_by_id(customer_id)

    return render_template('customers/form.html', customer=customer, action_title="Edit Customer Profile")
