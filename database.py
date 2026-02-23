"""
database.py
===========
Database connection and session management
"""

import os
from typing import Generator
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'lok_sabha_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# Create connection pool for better performance
connection_pool = pooling.MySQLConnectionPool(
    pool_name="lok_sabha_pool",
    pool_size=10,
    pool_reset_session=True,
    **DB_CONFIG
)

def get_db() -> Generator:
    """
    Get database connection from pool
    Usage in FastAPI endpoints:
        def endpoint(db = Depends(get_db)):
            cursor = db.cursor(dictionary=True)
            ...
    """
    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
    finally:
        if connection and connection.is_connected():
            connection.close()

def test_connection():
    """Test database connection"""
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False