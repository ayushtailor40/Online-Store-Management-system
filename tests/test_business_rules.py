import os
import unittest
from app import create_app
from config import TestingConfig
from init_db import init_sqlite
from database.db import query_db, get_db_connection
from services.auth_service import authenticate_admin
from services.product_service import create_product, delete_product, get_product_by_id
from services.category_service import create_category, delete_category
from services.customer_service import create_customer
from services.order_service import create_order, update_order_status, get_order_by_id
from services.analytics_service import get_dashboard_kpis
from services.report_service import generate_sales_report_csv


class SmartStoreBusinessRulesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test app with testing config
        cls.app = create_app(TestingConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        # Initialize clean test SQLite database
        test_db_path = os.path.join(os.path.dirname(__file__), 'test_online_store.db')
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

    def test_01_admin_authentication(self):
        """Test admin authentication with valid and invalid credentials."""
        admin = authenticate_admin('admin', 'Admin@123')
        self.assertIsNotNone(admin)
        self.assertEqual(admin['username'], 'admin')

        invalid_admin = authenticate_admin('admin', 'WrongPassword!')
        self.assertIsNone(invalid_admin)

    def test_02_product_creation_and_unit_profit(self):
        """Test product creation and calculation of unit profit margin."""
        data = {
            'sku': 'TEST-SKU-999',
            'name': 'Test Wireless Mouse',
            'category_id': 1,
            'description': 'Test product description',
            'cost_price': '40.00',
            'selling_price': '90.00',
            'stock_quantity': '25',
            'reorder_level': '5',
            'image_url': '',
            'is_active': 1
        }
        success, msg, prod_id = create_product(data)
        self.assertTrue(success, msg)
        self.assertIsNotNone(prod_id)

        # Retrieve and verify profit calculation
        prod = get_product_by_id(prod_id)
        self.assertEqual(float(prod['unit_profit']), 50.00)
        self.assertEqual(prod['stock_quantity'], 25)

    def test_03_order_creation_and_atomic_stock_deduction(self):
        """Test order creation, price snapshotting, and atomic stock deduction."""
        # Check stock before order
        prod_before = get_product_by_id(1)  # Sony WH-1000XM5
        stock_before = prod_before['stock_quantity']
        self.assertGreater(stock_before, 2)

        items = [{'product_id': 1, 'quantity': 2}]
        order_id, order_number = create_order(
            customer_id=1,
            items=items,
            payment_method='Credit Card',
            notes='Test order creation'
        )
        self.assertIsNotNone(order_id)
        self.assertTrue(order_number.startswith('ORD-'))

        # Check stock after order: must be exactly stock_before - 2
        prod_after = get_product_by_id(1)
        self.assertEqual(prod_after['stock_quantity'], stock_before - 2)

        # Verify order snapshot
        order = get_order_by_id(order_id)
        self.assertEqual(len(order['items']), 1)
        self.assertEqual(order['items'][0]['quantity'], 2)
        self.assertEqual(float(order['items'][0]['unit_price']), float(prod_before['selling_price']))
        self.assertEqual(order['status'], 'Confirmed')

    def test_04_insufficient_stock_rejection(self):
        """Test that orders with quantity exceeding stock are rejected and rolled back."""
        prod = get_product_by_id(2)
        current_stock = prod['stock_quantity']
        excessive_qty = current_stock + 100

        with self.assertRaises(ValueError) as ctx:
            create_order(
                customer_id=1,
                items=[{'product_id': 2, 'quantity': excessive_qty}],
                payment_method='Credit Card'
            )
        self.assertIn("Insufficient stock", str(ctx.exception))

        # Stock must remain unchanged
        prod_after = get_product_by_id(2)
        self.assertEqual(prod_after['stock_quantity'], current_stock)

    def test_05_single_stock_deduction_invariant(self):
        """Test that advancing order status does not re-deduct stock."""
        prod_before = get_product_by_id(5)
        stock_initial = prod_before['stock_quantity']

        order_id, _ = create_order(customer_id=2, items=[{'product_id': 5, 'quantity': 1}], payment_method='UPI')
        prod_after_order = get_product_by_id(5)
        self.assertEqual(prod_after_order['stock_quantity'], stock_initial - 1)

        # Transition Confirmed -> Shipped
        update_order_status(order_id, 'Shipped')
        prod_after_shipped = get_product_by_id(5)
        self.assertEqual(prod_after_shipped['stock_quantity'], stock_initial - 1)

        # Transition Shipped -> Delivered
        update_order_status(order_id, 'Delivered')
        prod_after_delivered = get_product_by_id(5)
        self.assertEqual(prod_after_delivered['stock_quantity'], stock_initial - 1)

    def test_06_order_cancellation_and_exact_restoration(self):
        """Test that cancelling an order restores stock exactly once, preventing double restoration."""
        prod = get_product_by_id(3)
        stock_init = prod['stock_quantity']

        # Place order for 3 items
        order_id, _ = create_order(customer_id=3, items=[{'product_id': 3, 'quantity': 3}], payment_method='Credit Card')
        self.assertEqual(get_product_by_id(3)['stock_quantity'], stock_init - 3)

        # Cancel order
        success, msg = update_order_status(order_id, 'Cancelled')
        self.assertTrue(success)

        # Stock must be restored to stock_init
        self.assertEqual(get_product_by_id(3)['stock_quantity'], stock_init)

        # Verify stock_restored flag
        order = get_order_by_id(order_id)
        self.assertEqual(order['stock_restored'], 1)
        self.assertEqual(order['status'], 'Cancelled')

        # Attempting to cancel or update again must not restore stock a second time
        success2, msg2 = update_order_status(order_id, 'Cancelled')
        self.assertEqual(get_product_by_id(3)['stock_quantity'], stock_init)

    def test_07_safe_product_deletion(self):
        """Test that products referenced by historical orders cannot be deleted."""
        # Product 1 is ordered in test_03, so it has historical order items
        success, msg = delete_product(1)
        self.assertFalse(success)
        self.assertIn("historical order", msg)

        # Product without orders can be deleted safely
        success_create, _, temp_id = create_product({
            'sku': 'TEMP-DELETE-001',
            'name': 'Temporary Product',
            'category_id': 1,
            'cost_price': '10',
            'selling_price': '20',
            'stock_quantity': '5',
            'reorder_level': '1'
        })
        self.assertTrue(success_create)
        success_del, _ = delete_product(temp_id)
        self.assertTrue(success_del)

    def test_08_safe_category_deletion(self):
        """Test that categories with active products cannot be deleted."""
        # Category 1 has products
        success, msg = delete_category(1)
        self.assertFalse(success)
        self.assertIn("assigned to it", msg)

        # Empty category can be deleted
        success_cat, new_cat_id = create_category("Empty Test Category", "Temporary")
        self.assertTrue(success_cat)
        success_cat_del, _ = delete_category(new_cat_id)
        self.assertTrue(success_cat_del)

    def test_09_analytics_profit_and_revenue(self):
        """Test that analytics calculations accurately reflect orders and profit."""
        kpis = get_dashboard_kpis()
        self.assertGreater(kpis['total_revenue'], 0)
        self.assertGreater(kpis['total_profit'], 0)
        self.assertLess(kpis['total_profit'], kpis['total_revenue'])
        self.assertGreater(kpis['total_orders'], 0)

    def test_10_csv_report_generation(self):
        """Test that CSV report outputs non-empty sanitized string."""
        csv_data = generate_sales_report_csv()
        self.assertIn("Order Number", csv_data)
        self.assertIn("Total Revenue", csv_data)
        self.assertIn("Profit", csv_data)
        self.assertGreater(len(csv_data), 100)


if __name__ == '__main__':
    unittest.main()
