import math
import uuid
from datetime import datetime
from database.db import query_db, transaction_scope, get_driver_name


def get_orders(
    search=None,
    status=None,
    payment_status=None,
    customer_id=None,
    start_date=None,
    end_date=None,
    page=1,
    per_page=10,
    sort_by='date',
    sort_order='desc'
):
    """
    Retrieves filtered, sorted, and paginated orders with customer name and item counts.
    """
    params = []
    where_clauses = []

    if customer_id:
        where_clauses.append("o.customer_id = %s")
        params.append(customer_id)

    if status and status != 'all':
        where_clauses.append("o.status = %s")
        params.append(status)

    if payment_status and payment_status != 'all':
        where_clauses.append("o.payment_status = %s")
        params.append(payment_status)

    if start_date:
        where_clauses.append("DATE(o.order_date) >= %s")
        params.append(start_date)

    if end_date:
        where_clauses.append("DATE(o.order_date) <= %s")
        params.append(end_date)

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append("(o.order_number LIKE %s OR c.name LIKE %s OR c.email LIKE %s)")
        params.extend([search_term, search_term, search_term])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_query = f"""
        SELECT COUNT(DISTINCT o.id) AS total
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        {where_sql}
    """
    total_result = query_db(count_query, tuple(params), one=True)
    total_count = total_result['total'] if total_result else 0

    total_pages = max(1, math.ceil(total_count / per_page))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    sort_mapping = {
        'date': 'o.order_date',
        'order_number': 'o.order_number',
        'customer': 'c.name',
        'amount': 'o.total_amount',
        'status': 'o.status'
    }
    col = sort_mapping.get(sort_by, 'o.order_date')
    direction = 'DESC' if str(sort_order).lower() == 'desc' else 'ASC'

    query = f"""
        SELECT 
            o.id,
            o.order_number,
            o.customer_id,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            o.order_date,
            o.status,
            o.payment_status,
            o.total_amount,
            o.total_cost,
            ROUND(o.total_amount - o.total_cost, 2) AS profit,
            o.stock_restored,
            o.notes,
            COUNT(oi.id) AS item_count,
            COALESCE(p.payment_method, 'None') AS payment_method
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN payments p ON o.id = p.order_id
        {where_sql}
        GROUP BY 
            o.id, o.order_number, o.customer_id, c.name, c.email, c.phone,
            o.order_date, o.status, o.payment_status, o.total_amount, o.total_cost,
            o.stock_restored, o.notes, p.payment_method
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


def get_order_by_id(order_id):
    """
    Fetches full order details including:
    - Header and customer info
    - List of line items with snapshot pricing and profit
    - Payment information
    """
    order_query = """
        SELECT 
            o.id,
            o.order_number,
            o.customer_id,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            c.address AS customer_address,
            c.city AS customer_city,
            c.state AS customer_state,
            c.postal_code AS customer_postal_code,
            o.order_date,
            o.status,
            o.payment_status,
            o.total_amount,
            o.total_cost,
            ROUND(o.total_amount - o.total_cost, 2) AS profit,
            o.stock_restored,
            o.notes,
            o.created_at,
            o.updated_at
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = %s
    """
    order = query_db(order_query, (order_id,), one=True)
    if not order:
        return None

    # Line items
    items_query = """
        SELECT 
            oi.id,
            oi.product_id,
            p.name AS product_name,
            p.sku AS product_sku,
            p.image_url,
            oi.quantity,
            oi.unit_price,
            oi.unit_cost,
            oi.subtotal,
            oi.profit
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
        ORDER BY oi.id ASC
    """
    order['items'] = query_db(items_query, (order_id,))

    # Payment info
    payment_query = """
        SELECT id, payment_date, amount, payment_method, transaction_id, status
        FROM payments
        WHERE order_id = %s
        ORDER BY id DESC
        LIMIT 1
    """
    order['payment'] = query_db(payment_query, (order_id,), one=True)

    return order


def create_order(customer_id, items, payment_method='Credit Card', notes=''):
    """
    Atomic Order Placement Workflow:
    1. Validates customer and items.
    2. Checks product availability and stock quantity.
    3. Calculates line totals, snapshotted selling price, and unit cost.
    4. Deducts stock atomically for all products.
    5. Records inventory movements.
    6. Creates order, order_items, and payment records.
    7. Fully rolls back if any error or stock shortage is encountered.
    """
    if not customer_id:
        raise ValueError("A valid customer must be selected.")

    cust = query_db("SELECT id, name FROM customers WHERE id = %s", (customer_id,), one=True)
    if not cust:
        raise ValueError("Selected customer does not exist.")

    if not items or len(items) == 0:
        raise ValueError("An order must contain at least one product item.")

    # Consolidate duplicate product entries
    consolidated = {}
    for item in items:
        pid = int(item.get('product_id', 0))
        qty = int(item.get('quantity', 0))
        if pid <= 0 or qty <= 0:
            raise ValueError("All order items must have a valid product and a quantity of 1 or more.")
        consolidated[pid] = consolidated.get(pid, 0) + qty

    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_suffix = uuid.uuid4().hex[:4].upper()
    order_number = f"ORD-{now_str[:8]}-{rand_suffix}"

    with transaction_scope() as (conn, cursor):
        driver = get_driver_name(conn)

        # Step 1: Validate stock for all products
        validated_items = []
        total_amount = 0.0
        total_cost = 0.0

        for pid, qty in consolidated.items():
            if driver == 'sqlite':
                from database.db import adapt_query_for_sqlite
                cursor.execute("SELECT id, name, sku, cost_price, selling_price, stock_quantity, is_active FROM products WHERE id = ?", (pid,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Product ID {pid} was not found.")
                p = row
            else:
                cursor.execute("SELECT id, name, sku, cost_price, selling_price, stock_quantity, is_active FROM products WHERE id = %s", (pid,))
                p = cursor.fetchone()
                if not p:
                    raise ValueError(f"Product ID {pid} was not found.")

            if not p['is_active']:
                raise ValueError(f"Product '{p['name']}' is discontinued and cannot be ordered.")

            if p['stock_quantity'] < qty:
                raise ValueError(f"Insufficient stock for '{p['name']}'. In stock: {p['stock_quantity']}, Requested: {qty}.")

            unit_price = float(p['selling_price'])
            unit_cost = float(p['cost_price'])
            subtotal = round(qty * unit_price, 2)
            profit = round(qty * (unit_price - unit_cost), 2)

            total_amount += subtotal
            total_cost += round(qty * unit_cost, 2)

            validated_items.append({
                'product_id': pid,
                'name': p['name'],
                'sku': p['sku'],
                'quantity': qty,
                'unit_price': unit_price,
                'unit_cost': unit_cost,
                'subtotal': subtotal,
                'profit': profit,
                'previous_stock': p['stock_quantity'],
                'new_stock': p['stock_quantity'] - qty
            })

        total_amount = round(total_amount, 2)
        total_cost = round(total_cost, 2)

        # Payment status determination
        payment_status = 'Paid' if payment_method != 'Cash on Delivery' else 'Unpaid'
        order_status = 'Confirmed' if payment_status == 'Paid' else 'Pending'

        # Step 2: Insert into orders table
        if driver == 'sqlite':
            order_sql = """
                INSERT INTO orders 
                (order_number, customer_id, order_date, status, payment_status, total_amount, total_cost, stock_restored, notes, created_at, updated_at)
                VALUES (?, ?, datetime('now', 'localtime'), ?, ?, ?, ?, 0, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """
            cursor.execute(order_sql, (order_number, customer_id, order_status, payment_status, total_amount, total_cost, (notes or '').strip()))
            order_id = cursor.lastrowid
        else:
            order_sql = """
                INSERT INTO orders 
                (order_number, customer_id, order_date, status, payment_status, total_amount, total_cost, stock_restored, notes, created_at, updated_at)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, 0, %s, NOW(), NOW())
            """
            cursor.execute(order_sql, (order_number, customer_id, order_status, payment_status, total_amount, total_cost, (notes or '').strip()))
            order_id = cursor.lastrowid

        # Step 3: Insert order_items, deduct stock, and record inventory movement
        for item in validated_items:
            # 3a: Insert order_items
            if driver == 'sqlite':
                item_sql = """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost, subtotal, profit, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """
                cursor.execute(item_sql, (order_id, item['product_id'], item['quantity'], item['unit_price'], item['unit_cost'], item['subtotal'], item['profit']))
            else:
                item_sql = """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost, subtotal, profit, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(item_sql, (order_id, item['product_id'], item['quantity'], item['unit_price'], item['unit_cost'], item['subtotal'], item['profit']))

            # 3b: Atomically deduct stock from product
            if driver == 'sqlite':
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (item['quantity'], item['product_id']))
            else:
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s", (item['quantity'], item['product_id']))

            # 3c: Log inventory movement (SALE)
            if driver == 'sqlite':
                mov_sql = """
                    INSERT INTO inventory_movements 
                    (product_id, change_type, quantity, previous_stock, new_stock, reason, reference_id, created_at)
                    VALUES (?, 'SALE', ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """
                cursor.execute(mov_sql, (
                    item['product_id'], -item['quantity'], item['previous_stock'],
                    item['new_stock'], f"Order sale {order_number}", order_id
                ))
            else:
                mov_sql = """
                    INSERT INTO inventory_movements 
                    (product_id, change_type, quantity, previous_stock, new_stock, reason, reference_id, created_at)
                    VALUES (%s, 'SALE', %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(mov_sql, (
                    item['product_id'], -item['quantity'], item['previous_stock'],
                    item['new_stock'], f"Order sale {order_number}", order_id
                ))

        # Step 4: Record payment
        txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}" if payment_status == 'Paid' else None
        pay_status = 'Success' if payment_status == 'Paid' else 'Pending'
        if driver == 'sqlite':
            pay_sql = """
                INSERT INTO payments (order_id, payment_date, amount, payment_method, transaction_id, status, created_at)
                VALUES (?, datetime('now', 'localtime'), ?, ?, ?, ?, datetime('now', 'localtime'))
            """
            cursor.execute(pay_sql, (order_id, total_amount, payment_method, txn_id, pay_status))
        else:
            pay_sql = """
                INSERT INTO payments (order_id, payment_date, amount, payment_method, transaction_id, status, created_at)
                VALUES (%s, NOW(), %s, %s, %s, %s, NOW())
            """
            cursor.execute(pay_sql, (order_id, total_amount, payment_method, txn_id, pay_status))

    return order_id, order_number


def update_order_status(order_id, new_status):
    """
    Handles atomic status updates according to strict business rules:
    - Allowed statuses: Pending, Confirmed, Shipped, Delivered, Cancelled
    - Cannot modify already Cancelled orders.
    - When transitioning to 'Cancelled':
      - If stock_restored is 0, restores stock for each order item and logs 'RETURN_RESTOCK'.
      - Sets stock_restored = 1 to guarantee stock is NEVER restored twice!
      - Updates payment_status to 'Refunded' if it was 'Paid'.
    - When transitioning between Pending -> Confirmed -> Shipped -> Delivered:
      - Does NOT touch product stock or movement records (stock was already deducted at order placement).
    """
    valid_statuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']
    if new_status not in valid_statuses:
        return False, f"Invalid order status '{new_status}'."

    order = query_db("SELECT id, order_number, status, payment_status, stock_restored FROM orders WHERE id = %s", (order_id,), one=True)
    if not order:
        return False, "Order not found."

    current_status = order['status']
    if current_status == new_status:
        return True, f"Order status is already '{new_status}'."

    if current_status == 'Cancelled':
        return False, "This order is already Cancelled and cannot be changed."

    with transaction_scope() as (conn, cursor):
        driver = get_driver_name(conn)

        # Case 1: Cancellation
        if new_status == 'Cancelled':
            # Check stock_restored flag
            if order['stock_restored'] == 0:
                # Fetch all items for this order
                if driver == 'sqlite':
                    cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
                else:
                    cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
                items = cursor.fetchall()

                for it in items:
                    pid = it['product_id']
                    qty = it['quantity']

                    # Get current stock
                    if driver == 'sqlite':
                        cursor.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,))
                        p_row = cursor.fetchone()
                        curr_stock = p_row['stock_quantity'] if p_row else 0
                        new_stock = curr_stock + qty
                        cursor.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (qty, pid))
                        cursor.execute("""
                            INSERT INTO inventory_movements 
                            (product_id, change_type, quantity, previous_stock, new_stock, reason, reference_id, created_at)
                            VALUES (?, 'RETURN_RESTOCK', ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                        """, (pid, qty, curr_stock, new_stock, f"Restocked on cancellation of order {order['order_number']}", order_id))
                    else:
                        cursor.execute("SELECT stock_quantity FROM products WHERE id = %s", (pid,))
                        p_row = cursor.fetchone()
                        curr_stock = p_row['stock_quantity'] if p_row else 0
                        new_stock = curr_stock + qty
                        cursor.execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE id = %s", (qty, pid))
                        cursor.execute("""
                            INSERT INTO inventory_movements 
                            (product_id, change_type, quantity, previous_stock, new_stock, reason, reference_id, created_at)
                            VALUES (%s, 'RETURN_RESTOCK', %s, %s, %s, %s, %s, NOW())
                        """, (pid, qty, curr_stock, new_stock, f"Restocked on cancellation of order {order['order_number']}", order_id))

            # Update order status to Cancelled and mark stock_restored = 1
            new_pay_status = 'Refunded' if order['payment_status'] == 'Paid' else order['payment_status']
            if driver == 'sqlite':
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'Cancelled', stock_restored = 1, payment_status = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (new_pay_status, order_id))
            else:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'Cancelled', stock_restored = 1, payment_status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (new_pay_status, order_id))

            return True, f"Order {order['order_number']} has been cancelled and its inventory stock has been restored."

        # Case 2: Progression between Pending, Confirmed, Shipped, Delivered
        # (Stock is NOT deducted again, maintaining single deduction invariant)
        if driver == 'sqlite':
            cursor.execute("""
                UPDATE orders 
                SET status = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """, (new_status, order_id))
        else:
            cursor.execute("""
                UPDATE orders 
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """, (new_status, order_id))

    return True, f"Order status updated to '{new_status}' successfully."
