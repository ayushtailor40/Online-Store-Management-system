"""
Database Initialization & Seeding Script
========================================
Initializes the database schema and loads sample data.
Supports both MySQL (default) and SQLite (zero-config local/testing mode).

Usage:
    python init_db.py                 # Initializes and seeds based on .env
    python init_db.py --mysql         # Force initialize MySQL
    python init_db.py --sqlite        # Force initialize SQLite
    python init_db.py --reset         # Drops and recreates all tables
"""
import os
import sys
import argparse
import re
from config import Config

try:
    import mysql.connector
except ImportError:
    mysql = None


def read_sql_file(file_path):
    """Read an SQL file safely with UTF-8 encoding."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_sql_statements(sql_text):
    """
    Split SQL text into executable statements, stripping comments and delimiters.
    """
    statements = []
    # Strip multi-line comments /* ... */
    sql_text = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
    
    current_stmt = []
    in_single_quote = False
    in_double_quote = False
    escape_next = False

    for line in sql_text.splitlines():
        trimmed = line.strip()
        # Skip pure line comment
        if not in_single_quote and not in_double_quote and (trimmed.startswith('--') or trimmed.startswith('#')):
            continue

        chars = list(line)
        i = 0
        while i < len(chars):
            c = chars[i]
            if escape_next:
                current_stmt.append(c)
                escape_next = False
                i += 1
                continue

            if c == '\\':
                current_stmt.append(c)
                escape_next = True
                i += 1
                continue

            if c == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif c == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif c == ';' and not in_single_quote and not in_double_quote:
                stmt_str = "".join(current_stmt).strip()
                if stmt_str:
                    statements.append(stmt_str)
                current_stmt = []
                i += 1
                continue

            current_stmt.append(c)
            i += 1
        current_stmt.append('\n')

    remaining = "".join(current_stmt).strip()
    if remaining:
        statements.append(remaining)

    return statements


def init_mysql():
    """Initializes MySQL database using database/schema.sql and database/sample_data.sql."""
    print("Connecting to MySQL server...")
    if mysql is None:
        print("Error: mysql-connector-python is not installed.")
        return False

    try:
        # Step 1: Connect to server without database to create DB if needed
        server_conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            autocommit=True
        )
        server_cursor = server_conn.cursor()
        print(f"Creating database `{Config.DB_NAME}` if not exists...")
        server_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        server_cursor.close()
        server_conn.close()

        # Step 2: Connect to specific database
        db_conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=False
        )
        cursor = db_conn.cursor()

        base_dir = os.path.dirname(__file__)
        schema_file = os.path.join(base_dir, 'database', 'schema.sql')
        sample_file = os.path.join(base_dir, 'database', 'sample_data.sql')

        print("Executing schema.sql...")
        schema_sql = read_sql_file(schema_file)
        schema_stmts = split_sql_statements(schema_sql)
        for stmt in schema_stmts:
            if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
                continue
            cursor.execute(stmt)
        db_conn.commit()
        print(f"Schema created successfully ({len(schema_stmts)} statements executed).")

        print("Executing sample_data.sql...")
        sample_sql = read_sql_file(sample_file)
        sample_stmts = split_sql_statements(sample_sql)
        for stmt in sample_stmts:
            if stmt.upper().startswith("USE "):
                continue
            cursor.execute(stmt)
        db_conn.commit()
        print(f"Sample data loaded successfully ({len(sample_stmts)} statements executed).")

        cursor.close()
        db_conn.close()
        print("\nMySQL database initialization completed successfully!")
        return True

    except mysql.connector.Error as err:
        print(f"\n[MySQL Error]: {err}")
        print("Tip: Check host, port, user, and password in .env file.")
        return False


def convert_mysql_schema_to_sqlite(mysql_sql):
    """Converts MySQL DDL statements to SQLite DDL syntax."""
    # Remove MySQL specific clauses: ENGINE=InnoDB, DEFAULT CHARSET=..., COLLATE=...
    cleaned = re.sub(r'ENGINE\s*=\s*\w+', '', mysql_sql, flags=re.IGNORECASE)
    cleaned = re.sub(r'DEFAULT\s+CHARSET\s*=\s*[\w_]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'COLLATE\s*=\s*[\w_]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'INT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bENUM\s*\([^)]*\)', 'TEXT', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bTINYINT\s*\(\d+\)', 'INTEGER', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bDATETIME\b', 'TEXT', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bTIMESTAMP\b', 'TEXT', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'ON\s+UPDATE\s+CURRENT_TIMESTAMP', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'SET\s+FOREIGN_KEY_CHECKS\s*=\s*[01];', '', cleaned, flags=re.IGNORECASE)

    # SQLite does not support inline INDEX definition inside CREATE TABLE.
    # We strip lines like: INDEX `idx_name` (`col`) or , INDEX `idx_name` (`col`)
    cleaned = re.sub(r',\s*INDEX\s+`?(\w+)`?\s*\([^)]+\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'INDEX\s+`?(\w+)`?\s*\([^)]+\)\s*,?', '', cleaned, flags=re.IGNORECASE)

    # Clean up any trailing commas before closing parenthesis
    cleaned = re.sub(r',\s*\)', ')', cleaned)
    return cleaned


def init_sqlite(db_path=None):
    """Initializes SQLite database using schema and sample data."""
    import sqlite3
    if db_path is None:
        db_path = Config.SQLITE_PATH

    print(f"Initializing SQLite database at: {db_path}")
    if os.path.exists(db_path) and db_path != ':memory:':
        try:
            os.remove(db_path)
            print("Removed existing SQLite database file.")
        except Exception:
            pass

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")

    base_dir = os.path.dirname(__file__)
    schema_file = os.path.join(base_dir, 'database', 'schema.sql')
    sample_file = os.path.join(base_dir, 'database', 'sample_data.sql')

    schema_sql = convert_mysql_schema_to_sqlite(read_sql_file(schema_file))
    schema_stmts = split_sql_statements(schema_sql)

    for stmt in schema_stmts:
        if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
            continue
        try:
            cursor.execute(stmt)
        except Exception as e:
            # Skip non-critical SQLite index / duplicate errors
            if "already exists" not in str(e).lower():
                print(f"Notice on SQLite DDL: {e} | Query: {stmt[:60]}...")

    conn.commit()

    sample_sql = read_sql_file(sample_file)
    sample_stmts = split_sql_statements(sample_sql)
    for stmt in sample_stmts:
        if stmt.upper().startswith("USE "):
            continue
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"Notice on SQLite Seed: {e} | Query: {stmt[:60]}...")

    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    conn.close()

    print(f"\nSQLite database initialized and seeded successfully at: {db_path}")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Initialize Smart Online Store Database")
    parser.add_argument('--mysql', action='store_true', help="Initialize MySQL database")
    parser.add_argument('--sqlite', action='store_true', help="Initialize SQLite database")
    args = parser.parse_args()

    if args.sqlite:
        init_sqlite()
    elif args.mysql:
        success = init_mysql()
        if not success:
            sys.exit(1)
    else:
        # Default behavior: Try MySQL first; if fails, offer or perform SQLite initialization
        print(f"Target DB Type from Config: {Config.DB_TYPE.upper()}")
        if Config.DB_TYPE == 'mysql':
            success = init_mysql()
            if not success:
                print("\n[Notice] MySQL initialization failed. Initializing SQLite local fallback database...")
                init_sqlite()
        else:
            init_sqlite()
