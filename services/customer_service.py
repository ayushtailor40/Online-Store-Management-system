import re
import math
from database.db import query_db, execute_insert, execute_update


EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")


def get_customers(search=None, page=1, per_page=10, sort_by='name', sort_order='asc'):
    """
    Retrieves customers with aggregated order statistics:
    - total_orders
    - total_spent (excluding cancelled orders)
    - is_repeat_customer (total_orders > 1)
    """
    params = []
    where_sql = ""

    if search:
        search_term = f"%{search.strip()}%"
        where_sql = "WHERE (c.name LIKE %s OR c.email LIKE %s OR c.phone LIKE %s OR c.city LIKE %s)"
        params.extend([search_term, search_term, search_term, search_term])

    count_query = f"SELECT COUNT(*) AS total FROM customers c {where_sql}"
    total_result = query_db(count_query, tuple(params), one=True)
    total_count = total_result['total'] if total_result else 0

    total_pages = max(1, math.ceil(total_count / per_page))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    sort_cols = {
        'name': 'c.name',
        'email': 'c.email',
        'city': 'c.city',
        'orders': 'total_orders',
        'spent': 'total_spent',
        'date': 'c.created_at'
    }
    col = sort_cols.get(sort_by, 'c.name')
    direction = 'DESC' if str(sort_order).lower() == 'desc' else 'ASC'

    query = f"""
        SELECT 
            c.id,
            c.name,
            c.email,
            c.phone,
            c.address,
            c.city,
            c.state,
            c.postal_code,
            c.created_at,
            COUNT(DISTINCT o.id) AS total_orders,
            COALESCE(SUM(CASE WHEN o.status != 'Cancelled' THEN o.total_amount ELSE 0 END), 0.00) AS total_spent,
            CASE WHEN COUNT(DISTINCT o.id) > 1 THEN 1 ELSE 0 END AS is_repeat
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        {where_sql}
        GROUP BY c.id, c.name, c.email, c.phone, c.address, c.city, c.state, c.postal_code, c.created_at
        ORDER BY {col} {direction}
        LIMIT %s OFFSET %s
    """
    query_params = list(params)
    query_params.extend([per_page, offset])

    items = query_db(query, tuple(query_params))

    return {
        'items': items,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }


def get_customer_by_id(customer_id):
    """Fetches single customer with their summary spending stats."""
    query = """
        SELECT 
            c.id,
            c.name,
            c.email,
            c.phone,
            c.address,
            c.city,
            c.state,
            c.postal_code,
            c.created_at,
            c.updated_at,
            COUNT(DISTINCT o.id) AS total_orders,
            COALESCE(SUM(CASE WHEN o.status != 'Cancelled' THEN o.total_amount ELSE 0 END), 0.00) AS total_spent,
            CASE WHEN COUNT(DISTINCT o.id) > 1 THEN 1 ELSE 0 END AS is_repeat
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        WHERE c.id = %s
        GROUP BY c.id, c.name, c.email, c.phone, c.address, c.city, c.state, c.postal_code, c.created_at, c.updated_at
    """
    return query_db(query, (customer_id,), one=True)


def get_customer_orders(customer_id):
    """Fetches all orders placed by this customer."""
    query = """
        SELECT 
            o.id,
            o.order_number,
            o.order_date,
            o.status,
            o.payment_status,
            o.total_amount,
            o.total_cost,
            ROUND(o.total_amount - o.total_cost, 2) AS profit,
            COUNT(oi.id) AS item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.customer_id = %s
        GROUP BY o.id, o.order_number, o.order_date, o.status, o.payment_status, o.total_amount, o.total_cost
        ORDER BY o.order_date DESC
    """
    return query_db(query, (customer_id,))


def validate_customer_data(data, customer_id=None):
    """Validates customer inputs and checks email uniqueness."""
    errors = []
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    city = (data.get('city') or '').strip()

    if not name:
        errors.append("Customer name is required.")
    elif len(name) > 100:
        errors.append("Name must not exceed 100 characters.")

    if not email:
        errors.append("Customer email is required.")
    elif not EMAIL_REGEX.match(email):
        errors.append("Please enter a valid email address.")
    else:
        # Check email duplicate
        if customer_id:
            existing = query_db("SELECT id FROM customers WHERE LOWER(email) = LOWER(%s) AND id != %s", (email, customer_id), one=True)
        else:
            existing = query_db("SELECT id FROM customers WHERE LOWER(email) = LOWER(%s)", (email,), one=True)
        if existing:
            errors.append(f"A customer with email '{email}' already exists.")

    if not city:
        errors.append("City is required.")

    cleaned = {
        'name': name,
        'email': email,
        'phone': phone or None,
        'address': (data.get('address') or '').strip() or None,
        'city': city,
        'state': (data.get('state') or '').strip() or None,
        'postal_code': (data.get('postal_code') or '').strip() or None
    }

    return (len(errors) == 0), errors, cleaned


def create_customer(data):
    """Creates a new customer record."""
    valid, errors, clean = validate_customer_data(data)
    if not valid:
        return False, errors, None

    query = """
        INSERT INTO customers (name, email, phone, address, city, state, postal_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    customer_id = execute_insert(query, (
        clean['name'], clean['email'], clean['phone'], clean['address'],
        clean['city'], clean['state'], clean['postal_code']
    ))
    return True, "Customer created successfully.", customer_id


def update_customer(customer_id, data):
    """Updates customer details."""
    valid, errors, clean = validate_customer_data(data, customer_id=customer_id)
    if not valid:
        return False, errors

    query = """
        UPDATE customers SET
            name = %s,
            email = %s,
            phone = %s,
            address = %s,
            city = %s,
            state = %s,
            postal_code = %s
        WHERE id = %s
    """
    execute_update(query, (
        clean['name'], clean['email'], clean['phone'], clean['address'],
        clean['city'], clean['state'], clean['postal_code'], customer_id
    ))
    return True, "Customer updated successfully."


def get_top_spending_customers(limit=5):
    """Returns the top spending customers."""
    query = """
        SELECT 
            c.id,
            c.name,
            c.email,
            c.city,
            COUNT(DISTINCT o.id) AS total_orders,
            COALESCE(SUM(o.total_amount), 0.00) AS total_spent
        FROM customers c
        INNER JOIN orders o ON c.id = o.customer_id AND o.status != 'Cancelled'
        GROUP BY c.id, c.name, c.email, c.city
        ORDER BY total_spent DESC
        LIMIT %s
    """
    return query_db(query, (limit,))
