import math
from database.db import query_db, transaction_scope, get_driver_name


def get_inventory_status(search=None, category_id=None, status_filter=None, page=1, per_page=10):
    """
    Retrieves current stock for all products, classified by stock status:
    - 'out_of_stock': stock_quantity == 0
    - 'low_stock': stock_quantity <= reorder_level AND stock_quantity > 0
    - 'in_stock': stock_quantity > reorder_level
    """
    params = []
    where_clauses = ["p.is_active = 1"]

    if category_id:
        where_clauses.append("p.category_id = %s")
        params.append(category_id)

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append("(p.name LIKE %s OR p.sku LIKE %s)")
        params.extend([search_term, search_term])

    if status_filter == 'out_of_stock':
        where_clauses.append("p.stock_quantity = 0")
    elif status_filter == 'low_stock':
        where_clauses.append("p.stock_quantity > 0 AND p.stock_quantity <= p.reorder_level")
    elif status_filter == 'in_stock':
        where_clauses.append("p.stock_quantity > p.reorder_level")

    where_sql = "WHERE " + " AND ".join(where_clauses)

    count_query = f"SELECT COUNT(*) AS total FROM products p {where_sql}"
    total_result = query_db(count_query, tuple(params), one=True)
    total_count = total_result['total'] if total_result else 0

    total_pages = max(1, math.ceil(total_count / per_page))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    query = f"""
        SELECT 
            p.id,
            p.sku,
            p.name,
            c.name AS category_name,
            p.cost_price,
            p.selling_price,
            p.stock_quantity,
            p.reorder_level,
            ROUND(p.stock_quantity * p.cost_price, 2) AS inventory_cost_value,
            ROUND(p.stock_quantity * p.selling_price, 2) AS inventory_retail_value,
            CASE 
                WHEN p.stock_quantity = 0 THEN 'out_of_stock'
                WHEN p.stock_quantity <= p.reorder_level THEN 'low_stock'
                ELSE 'in_stock'
            END AS status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        {where_sql}
        ORDER BY 
            CASE 
                WHEN p.stock_quantity = 0 THEN 1 
                WHEN p.stock_quantity <= p.reorder_level THEN 2 
                ELSE 3 
            END ASC,
            p.stock_quantity ASC
        LIMIT %s OFFSET %s
    """
    query_params = list(params)
    query_params.extend([per_page, offset])

    items = query_db(query, tuple(query_params))

    # Aggregated inventory summary totals
    summary_query = """
        SELECT 
            COUNT(*) AS total_skus,
            COALESCE(SUM(stock_quantity), 0) AS total_units,
            COALESCE(SUM(stock_quantity * cost_price), 0.00) AS total_cost_value,
            COALESCE(SUM(stock_quantity * selling_price), 0.00) AS total_retail_value,
            SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_count,
            SUM(CASE WHEN stock_quantity > 0 AND stock_quantity <= reorder_level THEN 1 ELSE 0 END) AS low_stock_count
        FROM products
        WHERE is_active = 1
    """
    summary = query_db(summary_query, one=True)

    return {
        'items': items,
        'summary': summary,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }


def adjust_stock(product_id, adjustment_type, quantity, reason):
    """
    Executes a manual stock adjustment atomically and logs the movement.
    adjustment_type: 'ADD' (incoming restock) or 'REMOVE' (write-off/damage/correction)
    """
    try:
        qty = int(quantity)
        if qty <= 0:
            return False, "Adjustment quantity must be greater than zero."
    except (ValueError, TypeError):
        return False, "Quantity must be an integer."

    reason = (reason or "").strip()
    if not reason:
        return False, "A reason for the stock adjustment is required."

    product = query_db("SELECT id, name, sku, stock_quantity FROM products WHERE id = %s", (product_id,), one=True)
    if not product:
        return False, "Product not found."

    current_stock = product['stock_quantity']

    if adjustment_type == 'ADD':
        new_stock = current_stock + qty
        change_type = 'IN'
        movement_qty = qty
    elif adjustment_type == 'REMOVE':
        if current_stock < qty:
            return False, f"Cannot remove {qty} units: Only {current_stock} units currently in stock."
        new_stock = current_stock - qty
        change_type = 'OUT'
        movement_qty = -qty
    else:
        return False, "Invalid adjustment type. Must be 'ADD' or 'REMOVE'."

    with transaction_scope() as (conn, cursor):
        driver = get_driver_name(conn)
        if driver == 'sqlite':
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_stock, product_id))
            mov_sql = """
                INSERT INTO inventory_movements 
                (product_id, change_type, quantity, previous_stock, new_stock, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """
            cursor.execute(mov_sql, (product_id, change_type, movement_qty, current_stock, new_stock, reason))
        else:
            cursor.execute("UPDATE products SET stock_quantity = %s WHERE id = %s", (new_stock, product_id))
            mov_sql = """
                INSERT INTO inventory_movements 
                (product_id, change_type, quantity, previous_stock, new_stock, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(mov_sql, (product_id, change_type, movement_qty, current_stock, new_stock, reason))

    return True, f"Stock for '{product['name']}' successfully updated from {current_stock} to {new_stock}."


def get_inventory_movements(product_id=None, limit=50):
    """
    Retrieves audit history log of stock changes.
    """
    params = []
    where_sql = ""
    if product_id:
        where_sql = "WHERE m.product_id = %s"
        params.append(product_id)

    query = f"""
        SELECT 
            m.id,
            m.product_id,
            p.name AS product_name,
            p.sku AS product_sku,
            m.change_type,
            m.quantity,
            m.previous_stock,
            m.new_stock,
            m.reason,
            m.reference_id,
            m.created_at
        FROM inventory_movements m
        JOIN products p ON m.product_id = p.id
        {where_sql}
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT %s
    """
    params.append(limit)
    return query_db(query, tuple(params))
