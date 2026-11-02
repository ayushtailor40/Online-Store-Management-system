# Smart Online Store Management & Data Analytics System

An enterprise-inspired, full-stack web application designed for comprehensive e-commerce operations, real-time inventory tracking, multi-channel sales management, and SQL-powered business intelligence analytics.

Built specifically with **Python Flask**, **MySQL**, **Vanilla JavaScript**, and **Chart.js** — without heavy frontend frameworks — making it clean, fully functional, and ideal for academic demonstrations, college mini-projects, and MCA data analytics evaluations.

---

## Table of Contents

1. [Key Features & Capabilities](#key-features--capabilities)
2. [Technology Stack](#technology-stack)
3. [System Architecture & Database Schema](#system-architecture--database-schema)
4. [Prerequisites](#prerequisites)
5. [Setup & Installation Guide (Windows & VS Code)](#setup--installation-guide-windows--vs-code)
   - [Step 1: Open in VS Code](#step-1-open-in-vs-code)
   - [Step 2: Create & Activate Virtual Environment](#step-2-create--activate-virtual-environment)
   - [Step 3: Install Dependencies](#step-3-install-dependencies)
   - [Step 4: Configure Database (`.env`)](#step-4-configure-database-env)
   - [Step 5: Initialize & Seed MySQL Database](#step-5-initialize--seed-mysql-database)
   - [Step 6: Run the Application](#step-6-run-the-application)
6. [Default Login Credentials](#default-login-credentials)
7. [Business Rules & Transaction Integrity](#business-rules--transaction-integrity)
8. [Automated Testing](#automated-testing)
9. [Troubleshooting Common Issues](#troubleshooting-common-issues)
10. [Viva / Project Defense Guide](#viva--project-defense-guide)

---

## 1. Key Features & Capabilities

### Modern SaaS Admin Dashboard
- **6 Real-time KPI Cards**: Total Revenue, Gross Profit, Total Orders, Total Customers, Active Products, and Low-Stock Alerts.
- **5 Interactive Chart.js Visualizations**:
  1. *Monthly Sales & Profit Trend* — Smooth dual-axis line chart tracking revenue and gross profit over time.
  2. *Revenue by Category* — Doughnut chart displaying product category share.
  3. *Top 10 Best-Selling Products* — Horizontal bar chart ranked by sales volume.
  4. *Gross Profit by Product* — Bar chart highlighting highest margin items.
  5. *Order Status Distribution* — Doughnut chart showing lifecycle states.
- **Interactive Period Filters**: All Time, 7 Days, 30 Days, 90 Days, Year-to-Date (YTD), 1 Year, or Custom Date Picker.
- **Category Filter**: Dynamically recalibrates dashboard charts and metrics for a specific product category.
- **Light & Dark Theme Toggle**: Persistent theme switcher stored in `localStorage`.

### Product & Category Management
- Full CRUD operations with server-side validation.
- Unit economic calculations: Calculates **Unit Profit** (`selling_price - cost_price`) and **Profit Margin %**.
- **Safe Deletion Protection**: Products referenced in historical orders cannot be deleted (preserves audit integrity; advises deactivation instead).
- Categories with associated active products cannot be deleted.
- Search, filter by stock status (In Stock, Low Stock, Out of Stock), sort by name, price, stock, SKU, and pagination.

### Customer Management & CRM
- Tracks customer contact details, city, and registration date.
- Aggregates lifetime spend (excluding cancelled orders) and total order counts.
- **Repeat Customer Identification**: Automatically tags returning customers (`orders > 1`).
- Top spenders leaderboard highlighting VIP accounts.

### Order Management & Transactional Fulfillment
- **Atomic Order Placement**: Deducts inventory stock using database transactions; if any product lacks sufficient stock, the entire order rolls back safely.
- **Historical Price Snapshotting**: Records unit selling price and cost price at the exact moment of purchase inside `order_items` (protects historical financial reports against future price changes).
- Order lifecycle states: `Pending`, `Confirmed`, `Shipped`, `Delivered`, `Cancelled`.
- **Single Deduction Invariant**: Advancing orders from Pending to Confirmed or Shipped never deducts stock a second time.
- **Safe Stock Restoration**: Cancelling an order restores inventory exactly once and sets `stock_restored = 1` to prevent duplicate restocks.

### Inventory Control & Audit Log
- Current stock levels with configurable reorder thresholds.
- Manual Stock Adjustment workflow (Add restocks or Remove damaged/written-off goods) requiring an audit reason.
- Immutable **Inventory Movement Log** recording all stock changes (`SALE`, `IN`, `OUT`, `RETURN_RESTOCK`, `ADJUSTMENT`).

### Advanced Data Analytics
- SQL aggregate queries calculating:
  - Daily sales and order volume
  - Category-wise comparisons
  - Slow-moving catalog items (lowest sales or zero sales)
  - Average Order Value (AOV)
  - Warehouse asset valuation at cost price vs. projected retail valuation

### Reports & CSV Export Center
- Export sanitized CSV files compatible with Microsoft Excel and Google Sheets:
  - Sales & Revenue Transactions CSV
  - Product Profitability & Margins CSV
  - Customer Lifetime Value (LTV) CSV
  - Inventory Stockout & Valuation CSV
- Formula injection protection: Automatically sanitizes cells starting with `=`, `+`, `-`, `@`.

---

## 2. Technology Stack

- **Backend**: Python 3.10+ / 3.13, Flask 3.x
- **Database**: MySQL 8.0+ (with automatic SQLite fallback for zero-config local testing)
- **Database Driver**: `mysql-connector-python`
- **Frontend**: HTML5, CSS3 (CSS Custom Properties design system), Vanilla JavaScript (ES6+)
- **Charts**: Chart.js 4.4
- **Icons**: Font Awesome 6.5
- **Testing**: `pytest` / `unittest`

---

## 3. System Architecture & Database Schema

The database `online_store_db` follows third normal form (3NF) relational design:

```
+----------------+       +-------------------+       +---------------------+
|   categories   | 1---N |     products      | 1---N |     order_items     |
+----------------+       +-------------------+       +---------------------+
                                   |                            |
                                   | 1---N                      | N---1
                                   v                            v
                         +-------------------+       +---------------------+
                         |inventory_movements|       |       orders        |
                         +-------------------+       +---------------------+
                                                                |
                                                                | 1---1 / 1---N
                                                                v
+----------------+       +-------------------+       +---------------------+
|     admins     |       |     customers     | 1---N |      payments       |
+----------------+       +-------------------+       +---------------------+
```

### Main Tables in `database/schema.sql`:
1. `admins`: Administrative credentials (scrypt-hashed), roles, and login history.
2. `categories`: Product classifications with active flags.
3. `products`: Catalog items, cost price, selling price, stock quantities, and reorder levels.
4. `customers`: Customer profiles and geographical locations.
5. `orders`: Order headers with timestamps, delivery statuses, payment states, and totals.
6. `order_items`: Line items with snapshotted unit costs, unit prices, and profits.
7. `payments`: Payment records, methods (Credit Card, UPI, Net Banking, COD), and transaction IDs.
8. `inventory_movements`: Immutable stock transaction ledger.

---

## 4. Prerequisites

Before starting, ensure you have:
1. **Python 3.10 or higher** installed on Windows.
   - Verify by opening PowerShell: `python --version`
   - Ensure *"Add python.exe to PATH"* was checked during installation.
2. **MySQL Server 8.0+** installed and running.
   - Verify service in PowerShell: `Get-Service -Name *mysql*`
   - Or installed via XAMPP / WampServer.
3. **Visual Studio Code** installed.

---

## 5. Setup & Installation Guide (Windows & VS Code)

### Step 1: Open in VS Code
1. Open Visual Studio Code.
2. Click **File &rarr; Open Folder...** and select `online_store_managment`.
3. Open a new terminal in VS Code: Press <kbd>Ctrl</kbd> + <kbd>`</kbd> (backtick) or select **Terminal &rarr; New Terminal**.

### Step 2: Create & Activate Virtual Environment
In the VS Code PowerShell terminal, run:

```powershell
# Create a virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

> **Tip:** If PowerShell displays an *Execution Policy* error, enable script execution:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### Step 3: Install Dependencies
Install all required libraries:

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Database (`.env`)
1. An `.env.example` file is provided in the project root.
2. Open `.env` and verify your MySQL credentials:

```ini
# Flask Secret Key
SECRET_KEY=smart-online-store-secret-key-2026

# Database Configuration
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=online_store_db

# App Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
ITEMS_PER_PAGE=10
```

> **Note:** Replace `your_mysql_password_here` with your actual MySQL `root` password.

### Step 5: Initialize & Seed MySQL Database

You can initialize and seed the database using any of the following 3 methods:

#### Method A: Using Python Helper (Recommended)
With your `.env` configured, run:
```powershell
python init_db.py --mysql
```
This automatically connects to MySQL, creates `online_store_db`, runs `database/schema.sql`, and populates demonstration records from `database/sample_data.sql`.

#### Method B: Using MySQL Command Line (CLI)
```powershell
# Replace with the path to your mysql.exe if not in PATH:
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "CREATE DATABASE IF NOT EXISTS online_store_db;"
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p online_store_db < database/schema.sql
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p online_store_db < database/sample_data.sql
```

#### Method C: Using MySQL Workbench
1. Open **MySQL Workbench** and connect to your local instance.
2. Click **File &rarr; Open SQL Script...** and select `database/schema.sql`. Click the lightning icon (<kbd>&#9889;</kbd>) to execute.
3. Click **File &rarr; Open SQL Script...** and select `database/sample_data.sql`. Click the lightning icon (<kbd>&#9889;</kbd>) to execute.

---

### Step 6: Run the Application

Start the Flask development server:

```powershell
python app.py
```

You will see output similar to:
```
Starting Smart Online Store Management System on http://127.0.0.1:5000
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Open your web browser and navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 6. Default Login Credentials

Access the administrative portal using the pre-seeded credentials:

| Field | Value |
|---|---|
| **URL** | `http://127.0.0.1:5000/login` |
| **Username** | `admin` |
| **Password** | `Admin@123` |
| **Role** | Super Administrator |

*(Passwords are hashed securely using the Werkzeug Scrypt algorithm with unique salt).*

---

## 7. Business Rules & Transaction Integrity

1. **Atomic Order Deduction**: When an order is placed, stock is decremented immediately within a MySQL transaction. If any item is short of stock, a `ValueError` is raised, rolling back all deductions.
2. **No Re-Deductions**: Changing an order status (e.g. from `Pending` &rarr; `Confirmed` &rarr; `Shipped` &rarr; `Delivered`) does **not** deduct stock again.
3. **Exact Stock Restoration**: When an order is cancelled:
   - Line items are inspected.
   - Stock is restored by the exact purchased quantity.
   - A `RETURN_RESTOCK` entry is recorded in `inventory_movements`.
   - The order's `stock_restored` flag is set to `1`.
   - Subsequent status modifications on cancelled orders are blocked.
4. **Historical Price Snapshotting**: Historical orders always use the `unit_price` and `unit_cost` recorded at checkout, preventing retrofitted calculations if catalog prices change later.
5. **Safe Referential Integrity**: Products that have historical sales in `order_items` cannot be deleted. The system advises archiving (`is_active = 0`) instead.

---

## 8. Automated Testing

The project includes an automated test suite verifying all critical business rules, atomic stock deductions, and web routes.

To run the test suite:

```powershell
python -m pytest tests/ -v
```

Expected result:
```
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_01_admin_authentication PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_02_product_creation_and_unit_profit PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_03_order_creation_and_atomic_stock_deduction PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_04_insufficient_stock_rejection PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_05_single_stock_deduction_invariant PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_06_order_cancellation_and_exact_restoration PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_07_safe_product_deletion PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_08_safe_category_deletion PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_09_analytics_profit_and_revenue PASSED
tests/test_business_rules.py::SmartStoreBusinessRulesTestCase::test_10_csv_report_generation PASSED
tests/test_routes.py::RoutesTestCase::... PASSED
============================= 21 passed in 2.76s ==============================
```

---

## 9. Troubleshooting Common Issues

### Issue 1: `ERROR 1045 (28000): Access denied for user 'root'@'localhost'`
- **Cause**: MySQL password in `.env` does not match your MySQL server root password.
- **Fix**: Open `.env` and set `DB_PASSWORD` to your actual MySQL root password. If your root account has no password, leave it empty: `DB_PASSWORD=`.

### Issue 2: `mysql.connector.errors.InterfaceError: Can't connect to MySQL server on 'localhost:3306'`
- **Cause**: The MySQL Windows service is stopped.
- **Fix**: Open PowerShell as Administrator and run:
  ```powershell
  Start-Service -Name MySQL80
  ```
  *(Or start MySQL from the XAMPP Control Panel).*

### Issue 3: Zero-Config SQLite Fallback Mode
If you need to test the project immediately on a machine where MySQL is not installed or configured:
- Change `DB_TYPE=sqlite` in `.env`.
- Run: `python init_db.py --sqlite`
- The system will run seamlessly with full functionality using `database/online_store.db`.

### Issue 4: Port 5000 is already in use
- **Fix**: Start on another port by running:
  ```powershell
  python -c "from app import app; app.run(port=5050, debug=True)"
  ```
  Or change `PORT=5050` in `.env`.

---

## 10. Viva / Project Defense Guide

During an academic viva or project demonstration, you may be asked the following questions:

**Q1: How do you prevent inventory race conditions or inconsistent order state?**
> *Answer:* We wrap order placement inside a database transaction (`with transaction_scope() as (conn, cursor):`). Before inserting the order, we query product stock with validation. We deduct stock and record the order items in the same transaction block. If any step fails (e.g. stock drops below requested quantity), the transaction executes a `ROLLBACK`, guaranteeing zero partial records.

**Q2: What is the difference between Gross Revenue and Gross Profit in your system?**
> *Answer:* Gross Revenue is the total sum of sales (`SUM(subtotal)` for completed orders). Gross Profit accounts for cost of goods sold (COGS): `SUM(quantity * (unit_price - unit_cost))`. We snaphot `unit_cost` and `unit_price` at the time of sale in `order_items` so that subsequent price changes in the product catalog do not corrupt historical profit reporting.

**Q3: How do you handle order cancellations?**
> *Answer:* When an order status transitions to `Cancelled`, we check `stock_restored == 0`. If not yet restored, we iterate over all order items, increment the product stock, create an inventory movement audit record with `change_type='RETURN_RESTOCK'`, and set `stock_restored = 1`. This ensures repeated clicks or updates never inflate stock multiple times.

**Q4: How do you guard against SQL Injection?**
> *Answer:* 100% of SQL queries across all services use parameterized queries with `%s` placeholders (e.g., `SELECT * FROM products WHERE id = %s`, `(product_id,)`). Parameter values are sent separately to the MySQL engine and never concatenated into SQL strings.

**Q5: How do you protect CSV exports against formula injection?**
> *Answer:* In `services/report_service.py`, every text cell passes through `sanitize_csv_cell()`. If a cell starts with dangerous formula trigger characters (`=`, `+`, `-`, `@`), it is automatically prepended with a single quote (`'`), preventing spreadsheet applications like Excel from interpreting cell contents as formulas.
