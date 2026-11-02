-- ====================================================================
-- Smart Online Store Management & Data Analytics System
-- Database Schema: online_store_db
-- Target Engine: MySQL 8.0+
-- ====================================================================

CREATE DATABASE IF NOT EXISTS `online_store_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `online_store_db`;

-- Set foreign key checks off during recreation
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `inventory_movements`;
DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `customers`;
DROP TABLE IF EXISTS `products`;
DROP TABLE IF EXISTS `categories`;
DROP TABLE IF EXISTS `admins`;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------------------------------------------
-- 1. Table: admins
-- Store administrative credentials and role metadata
-- --------------------------------------------------------------------
CREATE TABLE `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `role` VARCHAR(20) NOT NULL DEFAULT 'admin',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `last_login` TIMESTAMP NULL DEFAULT NULL,
    INDEX `idx_admin_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 2. Table: categories
-- Product categories hierarchy
-- --------------------------------------------------------------------
CREATE TABLE `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_categories_name` (`name`),
    INDEX `idx_categories_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 3. Table: products
-- Inventory items, pricing, reorder thresholds, and category references
-- --------------------------------------------------------------------
CREATE TABLE `products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `category_id` INT NOT NULL,
    `sku` VARCHAR(50) NOT NULL UNIQUE,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `cost_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `selling_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `stock_quantity` INT NOT NULL DEFAULT 0,
    `reorder_level` INT NOT NULL DEFAULT 5,
    `image_url` VARCHAR(500) DEFAULT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_products_category` 
        FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_products_category` (`category_id`),
    INDEX `idx_products_sku` (`sku`),
    INDEX `idx_products_stock` (`stock_quantity`),
    INDEX `idx_products_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 4. Table: customers
-- Registered customer profiles and contact details
-- --------------------------------------------------------------------
CREATE TABLE `customers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `phone` VARCHAR(25) DEFAULT NULL,
    `address` VARCHAR(255) DEFAULT NULL,
    `city` VARCHAR(100) NOT NULL,
    `state` VARCHAR(100) DEFAULT NULL,
    `postal_code` VARCHAR(20) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_customers_email` (`email`),
    INDEX `idx_customers_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 5. Table: orders
-- Customer sales orders header
-- --------------------------------------------------------------------
CREATE TABLE `orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_number` VARCHAR(32) NOT NULL UNIQUE,
    `customer_id` INT NOT NULL,
    `order_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status` ENUM('Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled') NOT NULL DEFAULT 'Pending',
    `payment_status` ENUM('Unpaid', 'Paid', 'Refunded') NOT NULL DEFAULT 'Unpaid',
    `total_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `total_cost` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `stock_restored` TINYINT(1) NOT NULL DEFAULT 0,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_orders_customer` 
        FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_orders_customer` (`customer_id`),
    INDEX `idx_orders_date` (`order_date`),
    INDEX `idx_orders_status` (`status`),
    INDEX `idx_orders_payment_status` (`payment_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 6. Table: order_items
-- Line items within an order with price & cost snapshot at sale time
-- --------------------------------------------------------------------
CREATE TABLE `order_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `quantity` INT NOT NULL,
    `unit_price` DECIMAL(10, 2) NOT NULL,
    `unit_cost` DECIMAL(10, 2) NOT NULL,
    `subtotal` DECIMAL(10, 2) NOT NULL,
    `profit` DECIMAL(10, 2) NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_order_items_order` 
        FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_order_items_product` 
        FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_order_items_order` (`order_id`),
    INDEX `idx_order_items_product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 7. Table: payments
-- Payment transactions associated with orders
-- --------------------------------------------------------------------
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `payment_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `amount` DECIMAL(10, 2) NOT NULL,
    `payment_method` ENUM('Credit Card', 'Debit Card', 'UPI', 'Net Banking', 'Cash on Delivery') NOT NULL DEFAULT 'Credit Card',
    `transaction_id` VARCHAR(100) DEFAULT NULL,
    `status` ENUM('Success', 'Pending', 'Failed') NOT NULL DEFAULT 'Success',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_payments_order` 
        FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX `idx_payments_order` (`order_id`),
    INDEX `idx_payments_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 8. Table: inventory_movements
-- Immutable audit log of all stock increases, decreases, sales, & returns
-- --------------------------------------------------------------------
CREATE TABLE `inventory_movements` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_id` INT NOT NULL,
    `change_type` ENUM('IN', 'OUT', 'SALE', 'RETURN_RESTOCK', 'ADJUSTMENT') NOT NULL,
    `quantity` INT NOT NULL,
    `previous_stock` INT NOT NULL,
    `new_stock` INT NOT NULL,
    `reason` VARCHAR(255) DEFAULT NULL,
    `reference_id` INT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_inventory_movements_product` 
        FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_inventory_product` (`product_id`),
    INDEX `idx_inventory_created` (`created_at`),
    INDEX `idx_inventory_type` (`change_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
