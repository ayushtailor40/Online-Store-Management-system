import os
import sqlite3
import re
from datetime import datetime
from contextlib import contextmanager
from flask import g, current_app
from config import Config

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None
    MySQLError = Exception


def adapt_query_for_sqlite(query: str) -> str:
    """
    Translates standard MySQL syntax to SQLite equivalents if SQLite is used.
    Handles placeholders (%s -> ?), DATE_FORMAT, NOW(), and common date functions.
    """
    # Replace MySQL DATE_FORMAT(col, '%Y-%m') -> strftime('%Y-%m', col)
    # Common pattern: DATE_FORMAT(col, '%Y-%m')
    query = re.sub(
        r"DATE_FORMAT\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*'([^']+)'\s*\)",
        r"strftime('\2', \1)",
        query,
        flags=re.IGNORECASE
    )
    # Replace NOW() -> datetime('now', 'localtime')
    query = re.sub(r"\bNOW\s*\(\s*\)", "datetime('now', 'localtime')", query, flags=re.IGNORECASE)
    # Replace CURDATE() -> date('now', 'localtime')
    query = re.sub(r"\bCURDATE\s*\(\s*\)", "date('now', 'localtime')", query, flags=re.IGNORECASE)
    # Replace IFNULL -> IFNULL (SQLite supports IFNULL)
    # Replace %s with ? for parameterized queries in SQLite
    query = query.replace("%s", "?")
    return query


def dict_factory(cursor, row):
    """Row factory for SQLite returning a standard dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def create_sqlite_connection(db_path: str):
    """Create and configure a SQLite connection with dict rows and helper functions."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = dict_factory
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Custom SQLite functions for MySQL compatibility if needed
    conn.create_function("MONTH", 1, lambda val: int(str(val)[5:7]) if val and len(str(val)) >= 7 else None)
    conn.create_function("YEAR", 1, lambda val: int(str(val)[:4]) if val and len(str(val)) >= 4 else None)
    return conn


def get_driver_name(conn) -> str:
    """Returns 'sqlite' if conn is sqlite3.Connection, otherwise 'mysql'."""
    if isinstance(conn, sqlite3.Connection):
        return 'sqlite'
    return 'mysql'


def get_db_connection(use_fallback: bool = True):
    """
    Acquires a database connection based on config.
    In a Flask application context, uses Flask's 'g' object for request-level connection reuse.
    Falls back gracefully to SQLite if MySQL is configured but fails to connect (e.g. wrong password or service stopped).
    """
    db_type = Config.DB_TYPE
    if current_app:
        db_type = current_app.config.get('DB_TYPE', Config.DB_TYPE)

    # Check if Flask context has an active connection
    try:
        if 'db' in g:
            return g.db
    except RuntimeError:
        # Outside Flask application context
        pass

    conn = None

    if db_type == 'mysql':
        try:
            if mysql is None:
                raise ImportError("mysql-connector-python is not installed")
            
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                autocommit=False,
                consume_results=True
            )
        except Exception as e:
            if not use_fallback:
                raise e
            # Graceful fallback to SQLite for local development/testing without MySQL running
            fallback_path = Config.SQLITE_PATH
            if current_app and current_app.config.get('SQLITE_PATH'):
                fallback_path = current_app.config.get('SQLITE_PATH')
            if fallback_path != ':memory:':
                os.makedirs(os.path.dirname(os.path.abspath(fallback_path)), exist_ok=True)
            conn = create_sqlite_connection(fallback_path)
    else:
        sqlite_path = Config.SQLITE_PATH
        if current_app and current_app.config.get('SQLITE_PATH'):
            sqlite_path = current_app.config.get('SQLITE_PATH')
        if sqlite_path != ':memory:':
            os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
        conn = create_sqlite_connection(sqlite_path)

    try:
        g.db = conn
    except RuntimeError:
        pass

    return conn


def close_db(e=None):
    """Close the request's database connection if one was opened."""
    try:
        db = g.pop('db', None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass


def is_mysql(conn=None) -> bool:
    """Check if current active connection is MySQL."""
    if conn is None:
        conn = get_db_connection()
    return not isinstance(conn, sqlite3.Connection)


def query_db(query: str, args: tuple = (), one: bool = False, commit: bool = False):
    """
    Executes a query and returns a list of dictionaries (or a single dict if one=True).
    Safe parameterized execution for both MySQL and SQLite.
    """
    conn = get_db_connection()
    driver = get_driver_name(conn)

    if driver == 'sqlite':
        actual_query = adapt_query_for_sqlite(query)
        cursor = conn.cursor()
        cursor.execute(actual_query, args)
        if commit:
            conn.commit()
            rowcount = cursor.rowcount
            cursor.close()
            return rowcount
        rv = cursor.fetchall()
        cursor.close()
        return (rv[0] if rv else None) if one else rv
    else:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, args)
            if commit:
                conn.commit()
                rowcount = cursor.rowcount
                cursor.close()
                return rowcount
            rv = cursor.fetchall()
            cursor.close()
            return (rv[0] if rv else None) if one else rv
        except Exception as e:
            cursor.close()
            raise e


def execute_insert(query: str, args: tuple = ()) -> int:
    """Executes an INSERT statement and returns the auto-increment primary key ID."""
    conn = get_db_connection()
    driver = get_driver_name(conn)

    if driver == 'sqlite':
        actual_query = adapt_query_for_sqlite(query)
        cursor = conn.cursor()
        cursor.execute(actual_query, args)
        last_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return last_id
    else:
        cursor = conn.cursor()
        try:
            cursor.execute(query, args)
            last_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            return last_id
        except Exception as e:
            conn.rollback()
            cursor.close()
            raise e


def execute_update(query: str, args: tuple = ()) -> int:
    """Executes an UPDATE or DELETE statement and returns the number of affected rows."""
    return query_db(query, args, commit=True)


@contextmanager
def transaction_scope():
    """
    Context manager for atomic database transactions.
    Usage:
        with transaction_scope() as (conn, cursor):
            cursor.execute(...)
            cursor.execute(...)
    Commits on exit if no exception, otherwise rolls back.
    """
    conn = get_db_connection()
    driver = get_driver_name(conn)
    
    if driver == 'sqlite':
        cursor = conn.cursor()
        try:
            yield conn, cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    else:
        cursor = conn.cursor(dictionary=True)
        try:
            yield conn, cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
