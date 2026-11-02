import math
from database.db import query_db, execute_insert, execute_update, transaction_scope, get_driver_name


def get_products(
    search=None,
    category_id=None,
    stock_status=None,
    sort_by='name',
    sort_order='asc',
    page=1,
    per_page=10,
    include_inactive=False
):
    """
    Retrieves filtered, sorted, and paginated products.
    Calculates unit profit (selling_price - cost_price).
    """
    params = []
    where_clauses = []

    if not include_inactive:
        where_clauses.append("p.is_active = 1")

    if category_id:
        where_clauses.append("p.category_id = %s")
        params.append(category_id)

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append("(p.name LIKE %s OR p.sku LIKE %s OR p.description LIKE %s)")
        params.extend([search_term, search_term, search_term])

    if stock_status == 'out_of_stock':
        where_clauses.append("p.stock_quantity = 0")
    elif stock_status == 'low_stock':
        where_clauses.append("p.stock_quantity > 0 AND p.stock_quantity <= p.reorder_level")
    elif stock_status == 'in_stock':
        where_clauses.append("p.stock_quantity > p.reorder_level")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count total matching rows
    count_query = f"""
        SELECT COUNT(*) AS total 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        {where_sql}
    """
    total_result = query_db(count_query, tuple(params), one=True)
    total_count = total_result['total'] if total_result else 0

    # Whitelist sorting columns to prevent SQL injection
    sort_mapping = {
        'name': 'p.name',
        'sku': 'p.sku',
        'price': 'p.selling_price',
        'cost': 'p.cost_price',
        'stock': 'p.stock_quantity',
        'category': 'c.name',
        'created_at': 'p.created_at'
    }
    col = sort_mapping.get(sort_by, 'p.name')
    direction = 'DESC' if str(sort_order).lower() == 'desc' else 'ASC'

    # Pagination calculation
    total_pages = max(1, math.ceil(total_count / per_page))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    query = f"""
        SELECT 
            p.id,
            p.category_id,
            c.name AS category_name,
            p.sku,
            p.name,
            p.description,
            p.cost_price,
            p.selling_price,
            ROUND(p.selling_price - p.cost_price, 2) AS unit_profit,
            CASE 
                WHEN p.cost_price > 0 THEN ROUND(((p.selling_price - p.cost_price) / p.cost_price) * 100, 1)
                ELSE 0.0 
            END AS profit_margin_percent,
            p.stock_quantity,
            p.reorder_level,
            p.image_url,
            p.is_active,
            p.created_at,
            p.updated_at,
            CASE 
                WHEN p.stock_quantity = 0 THEN 'out_of_stock'
                WHEN p.stock_quantity <= p.reorder_level THEN 'low_stock'
                ELSE 'in_stock'
            END AS stock_status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        {where_sql}
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


def get_product_by_id(product_id):
    """Fetches full product details by primary key."""
    query = """
        SELECT 
            p.id,
            p.category_id,
            c.name AS category_name,
            p.sku,
            p.name,
            p.description,
            p.cost_price,
            p.selling_price,
            ROUND(p.selling_price - p.cost_price, 2) AS unit_profit,
            CASE 
                WHEN p.cost_price > 0 THEN ROUND(((p.selling_price - p.cost_price) / p.cost_price) * 100, 1)
                ELSE 0.0 
            END AS profit_margin_percent,
            p.stock_quantity,
            p.reorder_level,
            p.image_url,
            p.is_active,
            p.created_at,
            p.updated_at,
            CASE 
                WHEN p.stock_quantity = 0 THEN 'out_of_stock'
                WHEN p.stock_quantity <= p.reorder_level THEN 'low_stock'
                ELSE 'in_stock'
            END AS stock_status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = %s
    """
    return query_db(query, (product_id,), one=True)


def validate_product_data(data, product_id=None):
    """Performs strict server-side validation for product fields."""
    errors = []
    
    sku = (data.get('sku') or '').strip().upper()
    name = (data.get('name') or '').strip()
    category_id = data.get('category_id')
    
    if not sku:
        errors.append("Product SKU is required.")
    elif len(sku) > 50:
        errors.append("SKU must not exceed 50 characters.")
    else:
        # Check SKU uniqueness
        if product_id:
            existing = query_db("SELECT id FROM products WHERE sku = %s AND id != %s", (sku, product_id), one=True)
        else:
            existing = query_db("SELECT id FROM products WHERE sku = %s", (sku,), one=True)
        if existing:
            errors.append(f"SKU '{sku}' is already in use by another product.")

    if not name:
        errors.append("Product name is required.")
    elif len(name) > 150:
        errors.append("Product name must not exceed 150 characters.")

    if not category_id:
        errors.append("Please select a category.")
    else:
        cat = query_db("SELECT id FROM categories WHERE id = %s", (category_id,), one=True)
        if not cat:
            errors.append("Selected category does not exist.")

    try:
        cost_price = float(data.get('cost_price', 0))
        if cost_price < 0:
            errors.append("Cost price cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Cost price must be a valid number.")
        cost_price = 0.0

    try:
        selling_price = float(data.get('selling_price', 0))
        if selling_price < 0:
            errors.append("Selling price cannot be negative.")
        elif selling_price < cost_price:
            errors.append("Selling price should ideally be greater than or equal to cost price.")
    except (ValueError, TypeError):
        errors.append("Selling price must be a valid number.")
        selling_price = 0.0

    try:
        stock_quantity = int(data.get('stock_quantity', 0))
        if stock_quantity < 0:
            errors.append("Stock quantity cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Stock quantity must be a valid integer.")
        stock_quantity = 0

    try:
        reorder_level = int(data.get('reorder_level', 5))
        if reorder_level < 0:
            errors.append("Reorder level cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Reorder level must be a valid integer.")
        reorder_level = 5

    cleaned_data = {
        'sku': sku,
        'name': name,
        'category_id': int(category_id) if category_id else None,
        'description': (data.get('description') or '').strip(),
        'cost_price': round(cost_price, 2),
        'selling_price': round(selling_price, 2),
        'stock_quantity': stock_quantity,
        'reorder_level': reorder_level,
        'image_url': (data.get('image_url') or '').strip() or None,
        'is_active': int(data.get('is_active', 1))
    }

    return (len(errors) == 0), errors, cleaned_data


def create_product(data):
    """
    Creates a new product and records initial inventory movement in a transaction.
    """
    valid, errors, clean = validate_product_data(data)
    if not valid:
        return False, errors, None

    with transaction_scope() as (conn, cursor):
        insert_query = """
            INSERT INTO products 
            (category_id, sku, name, description, cost_price, selling_price, stock_quantity, reorder_level, image_url, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Execute query depending on driver
        driver = get_driver_name(conn)
        if driver == 'sqlite':
            from database.db import adapt_query_for_sqlite
            cursor.execute(adapt_query_for_sqlite(insert_query), (
                clean['category_id'], clean['sku'], clean['name'], clean['description'],
                clean['cost_price'], clean['selling_price'], clean['stock_quantity'],
                clean['reorder_level'], clean['image_url'], clean['is_active']
            ))
            product_id = cursor.lastrowid
            
            # Log initial inventory if stock > 0
            if clean['stock_quantity'] > 0:
                mov_query = """
                    INSERT INTO inventory_movements 
                    (product_id, change_type, quantity, previous_stock, new_stock, reason, created_at)
                    VALUES (?, 'IN', ?, 0, ?, 'Initial inventory stock entry', datetime('now', 'localtime'))
                """
                cursor.execute(mov_query, (product_id, clean['stock_quantity'], clean['stock_quantity']))
        else:
            cursor.execute(insert_query, (
                clean['category_id'], clean['sku'], clean['name'], clean['description'],
                clean['cost_price'], clean['selling_price'], clean['stock_quantity'],
                clean['reorder_level'], clean['image_url'], clean['is_active']
            ))
            product_id = cursor.lastrowid
            
            if clean['stock_quantity'] > 0:
                mov_query = """
                    INSERT INTO inventory_movements 
                    (product_id, change_type, quantity, previous_stock, new_stock, reason, created_at)
                    VALUES (%s, 'IN', %s, 0, %s, 'Initial inventory stock entry', NOW())
                """
                cursor.execute(mov_query, (product_id, clean['stock_quantity'], clean['stock_quantity']))

    return True, "Product created successfully.", product_id


def update_product(product_id, data):
    """Updates existing product details with validation."""
    valid, errors, clean = validate_product_data(data, product_id=product_id)
    if not valid:
        return False, errors

    query = """
        UPDATE products SET 
            category_id = %s,
            sku = %s,
            name = %s,
            description = %s,
            cost_price = %s,
            selling_price = %s,
            reorder_level = %s,
            image_url = %s,
            is_active = %s
        WHERE id = %s
    """
    execute_update(query, (
        clean['category_id'], clean['sku'], clean['name'], clean['description'],
        clean['cost_price'], clean['selling_price'], clean['reorder_level'],
        clean['image_url'], clean['is_active'], product_id
    ))
    return True, "Product updated successfully."


def delete_product(product_id):
    """
    Safe product deletion.
    If the product has historical orders in `order_items`, prevent permanent deletion
    and return an informative message advising archival.
    """
    orders_check = query_db(
        "SELECT COUNT(*) AS order_count FROM order_items WHERE product_id = %s",
        (product_id,),
        one=True
    )
    count = orders_check['order_count'] if orders_check else 0
    if count > 0:
        return False, f"Cannot delete this product: It is referenced in {count} historical order(s). To preserve accounting records, please deactivate it instead of deleting."

    # Also clean up any orphan inventory movements if not tied to orders
    execute_update("DELETE FROM inventory_movements WHERE product_id = %s AND reference_id IS NULL", (product_id,))
    execute_update("DELETE FROM products WHERE id = %s", (product_id,))
    return True, "Product deleted safely."


def get_low_stock_products(limit=10):
    """Returns products currently at or below their reorder level."""
    query = """
        SELECT 
            p.id,
            p.sku,
            p.name,
            c.name AS category_name,
            p.stock_quantity,
            p.reorder_level,
            p.selling_price
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = 1 AND p.stock_quantity <= p.reorder_level
        ORDER BY p.stock_quantity ASC
        LIMIT %s
    """
    return query_db(query, (limit,))
