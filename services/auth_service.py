from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_db, execute_update


def authenticate_admin(username, password):
    """
    Validates admin credentials.
    Returns admin dict if valid, None otherwise.
    """
    if not username or not password:
        return None
    
    query = "SELECT * FROM admins WHERE username = %s LIMIT 1"
    admin = query_db(query, (username,), one=True)
    if not admin:
        return None

    if check_password_hash(admin['password_hash'], password):
        # Update last login timestamp
        execute_update("UPDATE admins SET last_login = NOW() WHERE id = %s", (admin['id'],))
        return admin

    return None


def get_admin_by_id(admin_id):
    """Fetches admin metadata by primary key ID."""
    query = "SELECT id, username, full_name, email, role, created_at, last_login FROM admins WHERE id = %s"
    return query_db(query, (admin_id,), one=True)


def update_admin_password(admin_id, old_password, new_password):
    """Updates admin password after verifying old password."""
    admin = query_db("SELECT password_hash FROM admins WHERE id = %s", (admin_id,), one=True)
    if not admin or not check_password_hash(admin['password_hash'], old_password):
        return False, "Current password does not match."
    
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
        
    new_hash = generate_password_hash(new_password)
    execute_update("UPDATE admins SET password_hash = %s WHERE id = %s", (new_hash, admin_id))
    return True, "Password updated successfully."
