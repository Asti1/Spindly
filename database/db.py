"""SQLite data layer for Spendly.

Provides three functions:
    get_db()   — returns a SQLite connection with row_factory and foreign keys enabled
    init_db()  — creates all tables using CREATE TABLE IF NOT EXISTS
    seed_db()  — inserts demo data for development (only once)
"""

import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

# Database file lives in the project root (parent of the database/ package),
# so the path resolves the same regardless of the current working directory.
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db")

# Fixed category list — keep in sync with the application.
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    """Open a connection to the SQLite database.

    Rows are returned as dict-like sqlite3.Row objects and foreign key
    enforcement is enabled on every connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database tables if they don't already exist.

    Safe to call multiple times.
    """
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses, only if the DB is empty.

    Returns early if the users table already contains data, so repeated runs
    never duplicate the seed data.
    """
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        # Dates spread across the current month, in YYYY-MM-DD format.
        month_prefix = datetime.now().strftime("%Y-%m-")

        # (amount, category, day, description) — at least one per category.
        sample_expenses = [
            (42.50, "Food", "02", "Groceries for the week"),
            (15.00, "Transport", "04", "Subway pass top-up"),
            (120.00, "Bills", "06", "Electricity bill"),
            (60.75, "Health", "09", "Pharmacy"),
            (35.00, "Entertainment", "12", "Movie tickets"),
            (89.99, "Shopping", "15", "New running shoes"),
            (22.40, "Other", "18", "Miscellaneous"),
            (18.25, "Food", "21", "Lunch with colleagues"),
        ]

        rows = [
            (user_id, amount, category, month_prefix + day, description)
            for amount, category, day, description in sample_expenses
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
