from datetime import datetime, timedelta
from database.db import query_db


def parse_date_range(preset='all', start_date=None, end_date=None):
    """
    Computes start and end date boundaries based on preset or custom dates.
    presets: 'today', '7d', '30d', '90d', 'ytd', '1y', 'all'
    """
    now = datetime.now()
    if preset == 'today':
        start = now.strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif preset == '7d':
        start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif preset == '30d':
        start = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif preset == '90d':
        start = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif preset == 'ytd':
        start = f"{now.year}-01-01"
        end = now.strftime('%Y-%m-%d')
    elif preset == '1y':
        start = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif preset == 'custom' and start_date and end_date:
        start = start_date
        end = end_date
    else:
        # Default all time
        start = None
        end = None
    return start, end


def get_dashboard_kpis(start_date=None, end_date=None, category_id=None):
    """
    Calculates the 6 main KPI metrics:
    1. Total Revenue (Delivered / Shipped / Confirmed, excluding Cancelled)
    2. Total Profit (Revenue minus snapshotted cost of items sold)
    3. Total Orders
    4. Total Customers
    5. Total Products
    6. Low-Stock Products Count
    Also calculates growth compared to previous period of identical duration.
    """
    where_clauses = ["o.status != 'Cancelled'"]
    params = []

    if start_date:
        where_clauses.append("DATE(o.order_date) >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("DATE(o.order_date) <= %s")
        params.append(end_date)
    if category_id:
        where_clauses.append("EXISTS (SELECT 1 FROM order_items oi2 JOIN products p2 ON oi2.product_id = p2.id WHERE oi2.order_id = o.id AND p2.category_id = %s)")
        params.append(category_id)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    kpi_query = f"""
        SELECT 
            COALESCE(SUM(o.total_amount), 0.00) AS total_revenue,
            COALESCE(SUM(o.total_amount - o.total_cost), 0.00) AS total_profit,
            COUNT(DISTINCT o.id) AS total_orders
        FROM orders o
        {where_sql}
    """
    kpi_data = query_db(kpi_query, tuple(params), one=True) or {'total_revenue': 0, 'total_profit': 0, 'total_orders': 0}

    # Customers & Products counts
    cust_count = query_db("SELECT COUNT(*) AS total FROM customers", one=True)['total']
    prod_count = query_db("SELECT COUNT(*) AS total FROM products WHERE is_active = 1", one=True)['total']
    low_stock = query_db("SELECT COUNT(*) AS total FROM products WHERE is_active = 1 AND stock_quantity <= reorder_level", one=True)['total']

    # Previous period calculation for growth metrics if date range is bounded
    growth_pct = 0.0
    if start_date and end_date:
        try:
            d_start = datetime.strptime(start_date, '%Y-%m-%d')
            d_end = datetime.strptime(end_date, '%Y-%m-%d')
            duration = (d_end - d_start).days
            if duration > 0:
                prev_end = (d_start - timedelta(days=1)).strftime('%Y-%m-%d')
                prev_start = (d_start - timedelta(days=duration + 1)).strftime('%Y-%m-%d')
                prev_query = """
                    SELECT COALESCE(SUM(total_amount), 0.00) AS prev_rev
                    FROM orders
                    WHERE status != 'Cancelled' AND DATE(order_date) >= %s AND DATE(order_date) <= %s
                """
                prev_res = query_db(prev_query, (prev_start, prev_end), one=True)
                prev_rev = float(prev_res['prev_rev']) if prev_res else 0.0
                curr_rev = float(kpi_data['total_revenue'])
                if prev_rev > 0:
                    growth_pct = round(((curr_rev - prev_rev) / prev_rev) * 100, 1)
        except Exception:
            growth_pct = 0.0

    return {
        'total_revenue': float(kpi_data['total_revenue']),
        'total_profit': float(kpi_data['total_profit']),
        'total_orders': int(kpi_data['total_orders']),
        'total_customers': int(cust_count),
        'total_products': int(prod_count),
        'low_stock_products': int(low_stock),
        'sales_growth_pct': growth_pct
    }


def get_monthly_sales_trend(months_limit=12):
    """
    Returns monthly revenue and order volume for the line chart.
    """
    query = """
        SELECT 
            DATE_FORMAT(order_date, '%Y-%m') AS month_key,
            COUNT(id) AS order_count,
            COALESCE(SUM(total_amount), 0.00) AS revenue,
            COALESCE(SUM(total_amount - total_cost), 0.00) AS profit
        FROM orders
        WHERE status != 'Cancelled'
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
        ORDER BY month_key ASC
        LIMIT %s
    """
    rows = query_db(query, (months_limit,))
    
    labels = []
    revenues = []
    profits = []
    order_counts = []

    for r in rows:
        labels.append(r['month_key'])
        revenues.append(float(r['revenue']))
        profits.append(float(r['profit']))
        order_counts.append(int(r['order_count']))

    return {
        'labels': labels,
        'revenues': revenues,
        'profits': profits,
        'order_counts': order_counts
    }


def get_revenue_by_category():
    """
    Returns revenue grouped by product category for the doughnut chart.
    """
    query = """
        SELECT 
            c.name AS category_name,
            COALESCE(SUM(oi.subtotal), 0.00) AS category_revenue
        FROM categories c
        JOIN products p ON c.id = p.category_id
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'Cancelled'
        GROUP BY c.id, c.name
        ORDER BY category_revenue DESC
    """
    rows = query_db(query)
    labels = [r['category_name'] for r in rows]
    data = [float(r['category_revenue']) for r in rows]
    return {'labels': labels, 'data': data}


def get_top_selling_products(limit=10):
    """
    Returns top 10 best-selling products by quantity and revenue for horizontal bar chart.
    """
    query = """
        SELECT 
            p.name AS product_name,
            p.sku,
            SUM(oi.quantity) AS total_units_sold,
            SUM(oi.subtotal) AS total_revenue
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'Cancelled'
        GROUP BY p.id, p.name, p.sku
        ORDER BY total_revenue DESC
        LIMIT %s
    """
    rows = query_db(query, (limit,))
    labels = [r['product_name'][:25] + ('...' if len(r['product_name']) > 25 else '') for r in rows]
    revenues = [float(r['total_revenue']) for r in rows]
    units = [int(r['total_units_sold']) for r in rows]
    return {'labels': labels, 'revenues': revenues, 'units': units, 'items': rows}


def get_profit_by_product(limit=10):
    """
    Returns top products ranked by gross profit generated.
    """
    query = """
        SELECT 
            p.name AS product_name,
            SUM(oi.profit) AS total_profit
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'Cancelled'
        GROUP BY p.id, p.name
        ORDER BY total_profit DESC
        LIMIT %s
    """
    rows = query_db(query, (limit,))
    labels = [r['product_name'][:25] + ('...' if len(r['product_name']) > 25 else '') for r in rows]
    profits = [float(r['total_profit']) for r in rows]
    return {'labels': labels, 'profits': profits}


def get_order_status_distribution():
    """
    Returns counts for all order statuses for the status doughnut chart.
    """
    query = """
        SELECT 
            status,
            COUNT(*) AS count
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """
    rows = query_db(query)
    labels = [r['status'] for r in rows]
    data = [int(r['count']) for r in rows]
    return {'labels': labels, 'data': data}


def get_comprehensive_analytics(preset='all', start_date=None, end_date=None):
    """
    Compiles full analytics dataset for the dedicated Analytics page.
    """
    start, end = parse_date_range(preset, start_date, end_date)
    where_orders = ["status != 'Cancelled'"]
    order_params = []
    if start:
        where_orders.append("DATE(order_date) >= %s")
        order_params.append(start)
    if end:
        where_orders.append("DATE(order_date) <= %s")
        order_params.append(end)

    orders_where_sql = "WHERE " + " AND ".join(where_orders)

    # 1. Sales & Revenue Summary
    summary_sql = f"""
        SELECT 
            COUNT(id) AS total_orders,
            COALESCE(SUM(total_amount), 0.00) AS total_revenue,
            COALESCE(SUM(total_amount - total_cost), 0.00) AS total_profit,
            COALESCE(AVG(total_amount), 0.00) AS average_order_value
        FROM orders
        {orders_where_sql}
    """
    sales_summary = query_db(summary_sql, tuple(order_params), one=True) or {}

    # 2. Daily / Weekly Sales
    daily_sql = f"""
        SELECT 
            DATE(order_date) AS order_day,
            COUNT(id) AS order_count,
            COALESCE(SUM(total_amount), 0.00) AS daily_revenue
        FROM orders
        {orders_where_sql}
        GROUP BY DATE(order_date)
        ORDER BY order_day DESC
        LIMIT 14
    """
    daily_sales = query_db(daily_sql, tuple(order_params))

    # 3. Slow Moving Products (0 or fewest sales)
    slow_sql = """
        SELECT 
            p.id,
            p.name,
            p.sku,
            c.name AS category_name,
            p.stock_quantity,
            p.selling_price,
            COALESCE(SUM(oi.quantity), 0) AS total_units_sold
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'Cancelled'
        WHERE p.is_active = 1
        GROUP BY p.id, p.name, p.sku, c.name, p.stock_quantity, p.selling_price
        ORDER BY total_units_sold ASC, p.stock_quantity DESC
        LIMIT 8
    """
    slow_moving = query_db(slow_sql)

    # 4. Customer Behavior Metrics
    cust_metrics_sql = """
        SELECT 
            COUNT(DISTINCT c.id) AS total_registered,
            SUM(CASE WHEN order_counts.cnt > 1 THEN 1 ELSE 0 END) AS repeat_customers,
            ROUND(AVG(order_counts.cnt), 1) AS avg_orders_per_customer
        FROM customers c
        LEFT JOIN (
            SELECT customer_id, COUNT(id) AS cnt 
            FROM orders 
            WHERE status != 'Cancelled' 
            GROUP BY customer_id
        ) order_counts ON c.id = order_counts.customer_id
    """
    customer_metrics = query_db(cust_metrics_sql, one=True) or {}

    # 5. Inventory Valuation Metrics
    inv_valuation_sql = """
        SELECT 
            COALESCE(SUM(stock_quantity * cost_price), 0.00) AS total_inventory_cost_value,
            COALESCE(SUM(stock_quantity * selling_price), 0.00) AS total_inventory_retail_value,
            SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_count,
            SUM(CASE WHEN stock_quantity > 0 AND stock_quantity <= reorder_level THEN 1 ELSE 0 END) AS low_stock_count
        FROM products
        WHERE is_active = 1
    """
    inventory_metrics = query_db(inv_valuation_sql, one=True) or {}

    # 6. Order Status Comparison (Delivered vs Cancelled)
    status_summary_sql = """
        SELECT 
            SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered_count,
            SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
            SUM(CASE WHEN status IN ('Pending', 'Confirmed', 'Shipped') THEN 1 ELSE 0 END) AS in_progress_count
        FROM orders
    """
    order_status_summary = query_db(status_summary_sql, one=True) or {}

    return {
        'sales_summary': sales_summary,
        'daily_sales': daily_sales,
        'slow_moving': slow_moving,
        'customer_metrics': customer_metrics,
        'inventory_metrics': inventory_metrics,
        'order_status_summary': order_status_summary,
        'date_filter': {'preset': preset, 'start_date': start, 'end_date': end}
    }
