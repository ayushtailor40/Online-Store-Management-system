from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.auth_service import authenticate_admin, get_admin_by_id

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator to enforce admin authentication on protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please sign in to access the management portal.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        next_url = request.form.get('next') or url_for('dashboard.index')

        admin = authenticate_admin(username, password)
        if admin:
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['full_name']
            session['admin_username'] = admin['username']
            session['admin_role'] = admin['role']
            flash(f"Welcome back, {admin['full_name']}!", "success")
            return redirect(next_url)
        else:
            flash("Invalid username or password. (Demo: admin / Admin@123)", "danger")

    return render_template('login.html', next=request.args.get('next', ''))


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
