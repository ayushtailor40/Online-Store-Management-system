import csv
import io
from database.db import query_db


def sanitize_csv_cell(value):
    """
    Sanitizes values to prevent CSV formula injection in spreadsheet applications (Excel, Calc).
    Prefixes values starting with '=', '+', '-', '@' with a single apostrophe.
    """
    if value is None:
        return ""
    str_val = str(value).strip()
    if str_val and str_val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{str_val}"
    return str_val


def generate_sales_report_csv(start_date=None, end_date=None, status=None):
    """Generates sales breakdown report CSV."""
    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("DATE(o.order_date) >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("DATE(o.order_date) <= %s")
        params.append(end_date)
    if status and status != 'all':
        where_clauses.append("o.status = %s")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT 
            o.order_number,
            DATE_FORMAT(o.order_date, '%Y-%m-%d %H:%i') AS order_datetime,
            c.name AS customer_name,
            c.email AS customer_email,
            c.city AS customer_city,
            o.status,
            o.payment_status,
            o.total_amount,
            o.total_cost,
            ROUND(o.total_amount - o.total_cost, 2) AS profit,
            COALESCE(p.payment_method, 'N/A') AS payment_method
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        LEFT JOIN payments p ON o.id = p.order_id
        {where_sql}
        ORDER BY o.order_date DESC
    """
    rows = query_db(query, tuple(params))

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Headers
    writer.writerow([
        "Order Number", "Order Date", "Customer Name", "Customer Email",
        "City", "Status", "Payment Status", "Total Revenue", "Total Cost", "Profit", "Payment Method"
    ])

    for r in rows:
        writer.writerow([
            sanitize_csv_cell(r['order_number']),
            sanitize_csv_cell(r['order_datetime']),
            sanitize_csv_cell(r['customer_name']),
            sanitize_csv_cell(r['customer_email']),
            sanitize_csv_cell(r['customer_city']),
            sanitize_csv_cell(r['status']),
            sanitize_csv_cell(r['payment_status']),
            f"{float(r['total_amount']):.2f}",
            f"{float(r['total_cost']):.2f}",
            f"{float(r['profit']):.2f}",
            sanitize_csv_cell(r['payment_method'])
        ])

    return output.getvalue()


def generate_product_performance_csv(category_id=None):
    """Generates product sales and profitability performance report CSV."""
    where_sql = ""
    params = []
    if category_id:
        where_sql = "WHERE p.category_id = %s"
        params.append(category_id)

    query = f"""
        SELECT 
            p.sku,
            p.name AS product_name,
            c.name AS category_name,
            p.cost_price,
            p.selling_price,
            ROUND(p.selling_price - p.cost_price, 2) AS unit_margin,
            p.stock_quantity,
            COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
            COALESCE(SUM(oi.subtotal), 0.00) AS total_revenue_generated,
            COALESCE(SUM(oi.profit), 0.00) AS total_profit_generated
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'Cancelled'
        {where_sql}
        GROUP BY p.id, p.sku, p.name, c.name, p.cost_price, p.selling_price, p.stock_quantity
        ORDER BY total_revenue_generated DESC
    """
    rows = query_db(query, tuple(params))

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "SKU", "Product Name", "Category", "Cost Price", "Selling Price",
        "Unit Margin", "Current Stock", "Units Sold", "Total Revenue", "Total Gross Profit"
    ])

    for r in rows:
        writer.writerow([
            sanitize_csv_cell(r['sku']),
            sanitize_csv_cell(r['product_name']),
            sanitize_csv_cell(r['category_name']),
            f"{float(r['cost_price']):.2f}",
            f"{float(r['selling_price']):.2f}",
            f"{float(r['unit_margin']):.2f}",
            r['stock_quantity'],
            r['total_units_sold'],
            f"{float(r['total_revenue_generated']):.2f}",
            f"{float(r['total_profit_generated']):.2f}"
        ])

    return output.getvalue()


def generate_customer_report_csv():
    """Generates customer lifetime value and activity report CSV."""
    query = """
        SELECT 
            c.id,
            c.name,
            c.email,
            c.phone,
            c.city,
            c.state,
            DATE_FORMAT(c.created_at, '%Y-%m-%d') AS registered_on,
            COUNT(DISTINCT o.id) AS total_orders,
            COALESCE(SUM(CASE WHEN o.status != 'Cancelled' THEN o.total_amount ELSE 0 END), 0.00) AS total_spent,
            CASE WHEN COUNT(DISTINCT o.id) > 1 THEN 'Yes' ELSE 'No' END AS is_repeat_customer
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name, c.email, c.phone, c.city, c.state, c.created_at
        ORDER BY total_spent DESC
    """
    rows = query_db(query)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "Customer ID", "Customer Name", "Email", "Phone", "City",
        "State", "Registered Date", "Total Orders", "Total Spent", "Repeat Customer"
    ])

    for r in rows:
        writer.writerow([
            r['id'],
            sanitize_csv_cell(r['name']),
            sanitize_csv_cell(r['email']),
            sanitize_csv_cell(r['phone']),
            sanitize_csv_cell(r['city']),
            sanitize_csv_cell(r['state']),
            sanitize_csv_cell(r['registered_on']),
            r['total_orders'],
            f"{float(r['total_spent']):.2f}",
            r['is_repeat_customer']
        ])

    return output.getvalue()


def generate_inventory_report_csv(status_filter=None):
    """Generates inventory stock valuation and health report CSV."""
    where_clauses = ["p.is_active = 1"]
    if status_filter == 'low_stock':
        where_clauses.append("p.stock_quantity <= p.reorder_level")
    elif status_filter == 'out_of_stock':
        where_clauses.append("p.stock_quantity = 0")

    where_sql = "WHERE " + " AND ".join(where_clauses)

    query = f"""
        SELECT 
            p.sku,
            p.name AS product_name,
            c.name AS category_name,
            p.cost_price,
            p.selling_price,
            p.stock_quantity,
            p.reorder_level,
            ROUND(p.stock_quantity * p.cost_price, 2) AS inventory_cost_value,
            ROUND(p.stock_quantity * p.selling_price, 2) AS inventory_retail_value,
            CASE 
                WHEN p.stock_quantity = 0 THEN 'Out of Stock'
                WHEN p.stock_quantity <= p.reorder_level THEN 'Low Stock'
                ELSE 'In Stock'
            END AS stock_status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        {where_sql}
        ORDER BY p.stock_quantity ASC
    """
    rows = query_db(query)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "SKU", "Product Name", "Category", "Cost Price", "Selling Price",
        "Stock Quantity", "Reorder Level", "Total Cost Value", "Total Retail Value", "Status"
    ])

    for r in rows:
        writer.writerow([
            sanitize_csv_cell(r['sku']),
            sanitize_csv_cell(r['product_name']),
            sanitize_csv_cell(r['category_name']),
            f"{float(r['cost_price']):.2f}",
            f"{float(r['selling_price']):.2f}",
            r['stock_quantity'],
            r['reorder_level'],
            f"{float(r['inventory_cost_value']):.2f}",
            f"{float(r['inventory_retail_value']):.2f}",
            r['stock_status']
        ])

    return output.getvalue()
