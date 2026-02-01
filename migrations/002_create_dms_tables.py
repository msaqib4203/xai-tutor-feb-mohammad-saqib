"""
Migration: Create users, folders, files tables
Version: 002
Description: Creates users, folders and files tables for the DMS
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DATABASE_PATH


def upgrade():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create migrations tracking table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check if this migration has already been applied
    cursor.execute("SELECT 1 FROM _migrations WHERE name = ?", ("002_create_dms_tables",))
    if cursor.fetchone():
        print("Migration 002_create_dms_tables already applied. Skipping.")
        conn.close()
        return

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    # Create folders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            parent_folder_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(parent_folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    """)

    # Create files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content BLOB,
            size INTEGER,
            mime_type TEXT,
            user_id INTEGER NOT NULL,
            parent_folder_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(parent_folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    """)

    # Record this migration
    cursor.execute("INSERT INTO _migrations (name) VALUES (?)", ("002_create_dms_tables",))

    conn.commit()
    conn.close()
    print("Migration 002_create_dms_tables applied successfully.")


def downgrade():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS files")
    cursor.execute("DROP TABLE IF EXISTS folders")
    cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("DELETE FROM _migrations WHERE name = ?", ("002_create_dms_tables",))

    conn.commit()
    conn.close()
    print("Migration 002_create_dms_tables reverted successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run database migration")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Migration action to perform"
    )

    args = parser.parse_args()

    if args.action == "upgrade":
        upgrade()
    elif args.action == "downgrade":
        downgrade()
