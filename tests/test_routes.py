import os
import unittest
from app import create_app
from config import TestingConfig
from init_db import init_sqlite


class RoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        test_db_path = os.path.join(os.path.dirname(__file__), 'test_routes_store.db')
        cls.test_db_path = test_db_path
        cls.app.config['SQLITE_PATH'] = test_db_path
        init_sqlite(test_db_path)

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        # Create fresh test client for each test to isolate session state
        self.client = self.app.test_client()

    def login(self):
        """Simulate admin login in test session."""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['admin_name'] = 'System Administrator'
            sess['admin_username'] = 'admin'
            sess['admin_role'] = 'superadmin'

    def test_unauthenticated_redirect(self):
        """Unauthenticated requests to protected routes redirect to login."""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_login_page_renders(self):
        """Login page renders with 200 OK when not authenticated."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SmartStore', response.data)

    def test_dashboard_renders(self):
        """Dashboard renders with 200 OK when logged in."""
        self.login()
        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Total Revenue', response.data)
        self.assertIn(b'Gross Profit', response.data)
        self.assertIn(b'Active Products', response.data)

    def test_dashboard_stats_api(self):
        """Dashboard API returns valid JSON stats and charts."""
        self.login()
        response = self.client.get('/api/dashboard/stats?preset=all')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('kpis', data)
        self.assertIn('charts', data)
        self.assertIn('total_revenue', data['kpis'])
        self.assertIn('monthly_trend', data['charts'])

    def test_products_page(self):
        """Products catalog page renders with table of items."""
        self.login()
        response = self.client.get('/products', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product Catalog Management', response.data)
        self.assertIn(b'Apple AirPods Max', response.data)

    def test_categories_page(self):
        """Categories page renders with category items."""
        self.login()
        response = self.client.get('/categories', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product Category Management', response.data)
        self.assertIn(b'Audio &amp; Headphones', response.data)

    def test_customers_page_and_details(self):
        """Customers list and customer details page render."""
        self.login()
        response = self.client.get('/customers', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Customer Accounts & Spending', response.data)

        # Details
        det_response = self.client.get('/customers/1', follow_redirects=True)
        self.assertEqual(det_response.status_code, 200)
        self.assertIn(b'Customer Profile:', det_response.data)

    def test_orders_page_and_details(self):
        """Orders list and single order invoice details render."""
        self.login()
        response = self.client.get('/orders', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order Management & Fulfillment', response.data)

        # Single order details
        ord_response = self.client.get('/orders/1', follow_redirects=True)
        self.assertEqual(ord_response.status_code, 200)
        self.assertIn(b'Order Invoice:', ord_response.data)

    def test_inventory_page(self):
        """Inventory management and stock movements render."""
        self.login()
        response = self.client.get('/inventory', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Warehouse Inventory & Stock Control', response.data)

    def test_analytics_page_and_api(self):
        """Analytics page and charts API render."""
        self.login()
        response = self.client.get('/analytics', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Advanced Data Analytics & Insights', response.data)

        api_res = self.client.get('/analytics/api/charts')
        self.assertEqual(api_res.status_code, 200)
        self.assertIn('monthly_trend', api_res.get_json())

    def test_reports_page_and_csv_exports(self):
        """Reports page renders and CSV exports return attachment content."""
        self.login()
        response = self.client.get('/reports', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Sales export
        sales_csv = self.client.get('/reports/export/sales')
        self.assertEqual(sales_csv.status_code, 200)
        self.assertEqual(sales_csv.mimetype, 'text/csv')
        self.assertIn(b'Order Number,Order Date', sales_csv.data)

        # Products export
        prod_csv = self.client.get('/reports/export/products')
        self.assertEqual(prod_csv.status_code, 200)
        self.assertIn(b'SKU,Product Name', prod_csv.data)

        # Customers export
        cust_csv = self.client.get('/reports/export/customers')
        self.assertEqual(cust_csv.status_code, 200)
        self.assertIn(b'Customer ID,Customer Name', cust_csv.data)

        # Inventory export
        inv_csv = self.client.get('/reports/export/inventory')
        self.assertEqual(inv_csv.status_code, 200)
        self.assertIn(b'SKU,Product Name,Category', inv_csv.data)


if __name__ == '__main__':
    unittest.main()
