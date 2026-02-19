#!/usr/bin/env python3
"""Test Supabase connection and run migration."""
import psycopg2
from urllib.parse import urlparse

# Parse the connection string
conn_string = "postgresql://postgres:dFQtKCm9kUdlznPq@db.aptlvvbrlypqmymfatnx.supabase.co:5432/postgres"

print("Testing connection to Supabase...")
print(f"URL: https://aptlvvbrlypqmymfatnx.supabase.co")

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    # Test query
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"Connected successfully!")
    print(f"PostgreSQL version: {version[0][:50]}...")
    
    # Check existing tables
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public';
    """)
    tables = [row[0] for row in cur.fetchall()]
    print(f"\nExisting tables: {tables}")
    
    cur.close()
    conn.close()
    print("\nConnection test PASSED!")
    
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()
