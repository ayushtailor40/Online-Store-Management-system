from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth import login_required
from services.category_service import (
    get_all_categories,
    get_category_by_id,
    create_category,
    update_category,
    delete_category
)

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')


@categories_bp.route('')
@categories_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    active_only = request.args.get('active_only') == '1'
    categories = get_all_categories(search=search, active_only=active_only)

    return render_template(
        'categories/index.html',
        categories=categories,
        search=search,
        active_only=active_only
    )


@categories_bp.route('/new', methods=['POST'])
@login_required
def new():
    name = request.form.get('name')
    description = request.form.get('description')
    success, message_or_id = create_category(name, description)
    if success:
        flash("Category created successfully.", "success")
    else:
        flash(message_or_id, "danger")
    return redirect(url_for('categories.index'))


@categories_bp.route('/<int:category_id>/edit', methods=['POST'])
@login_required
def edit(category_id):
    name = request.form.get('name')
    description = request.form.get('description')
    is_active = 1 if request.form.get('is_active') else 0
    success, message = update_category(category_id, name, description, is_active)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('categories.index'))


@categories_bp.route('/<int:category_id>/delete', methods=['POST'])
@login_required
def delete(category_id):
    success, message = delete_category(category_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for('categories.index'))
