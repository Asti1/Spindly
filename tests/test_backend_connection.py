"""Tests for Step 5 — Backend Connection.

Covers:
  - Unit tests for all four query helpers in database/queries.py
  - Route tests for GET /profile (unauthenticated and authenticated)

All tests use a temporary SQLite database so the real expense_tracker.db
is never touched.
"""

import pytest

import database.db as db_module
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

_ORIGINAL_DB_PATH = db_module.DB_PATH


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """Patch DB_PATH to a temporary file and seed it."""
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", path)
    db_module.init_db()
    db_module.seed_db()
    yield path


@pytest.fixture()
def app(db_path):
    """Flask test application wired to the temporary database."""
    import importlib
    import app as flask_app

    # Reload so app-level init_db/seed_db runs against the temp DB.
    importlib.reload(flask_app)

    flask_app.app.config["TESTING"] = True
    flask_app.app.config["SECRET_KEY"] = "test-secret"
    yield flask_app.app


@pytest.fixture()
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture()
def auth_client(app):
    """Test client with an active session for user_id=1 (Demo User)."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"
    return client


# ------------------------------------------------------------------ #
# Unit tests — get_user_by_id                                         #
# ------------------------------------------------------------------ #

class TestGetUserById:
    def test_existing_user_returns_dict(self, db_path):
        user = get_user_by_id(1)
        assert user is not None
        assert isinstance(user, dict)

    def test_existing_user_name(self, db_path):
        user = get_user_by_id(1)
        assert user["name"] == "Demo User"

    def test_existing_user_email(self, db_path):
        user = get_user_by_id(1)
        assert user["email"] == "demo@spendly.com"

    def test_existing_user_member_since_format(self, db_path):
        """member_since should be formatted as 'Month YYYY', e.g. 'June 2026'."""
        user = get_user_by_id(1)
        assert "member_since" in user
        parts = user["member_since"].split()
        assert len(parts) == 2, f"Expected 'Month YYYY', got {user['member_since']!r}"
        assert parts[1].isdigit() and len(parts[1]) == 4

    def test_missing_user_returns_none(self, db_path):
        assert get_user_by_id(9999) is None


# ------------------------------------------------------------------ #
# Unit tests — get_summary_stats                                      #
# ------------------------------------------------------------------ #

class TestGetSummaryStats:
    def test_transaction_count(self, db_path):
        stats = get_summary_stats(1)
        assert stats["transaction_count"] == 8

    def test_total_spent(self, db_path):
        # Seed amounts: 42.50+15.00+120.00+60.75+35.00+89.99+22.40+18.25
        expected = round(42.50 + 15.00 + 120.00 + 60.75 + 35.00 + 89.99 + 22.40 + 18.25, 2)
        stats = get_summary_stats(1)
        assert round(stats["total_spent"], 2) == expected

    def test_top_category(self, db_path):
        stats = get_summary_stats(1)
        assert stats["top_category"] == "Bills"

    def test_unknown_user_returns_zeros(self, db_path):
        stats = get_summary_stats(9999)
        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ------------------------------------------------------------------ #
# Unit tests — get_recent_transactions                                #
# ------------------------------------------------------------------ #

class TestGetRecentTransactions:
    def test_returns_eight_items(self, db_path):
        txns = get_recent_transactions(1)
        assert len(txns) == 8

    def test_returns_list(self, db_path):
        txns = get_recent_transactions(1)
        assert isinstance(txns, list)

    def test_items_have_required_keys(self, db_path):
        txns = get_recent_transactions(1)
        for txn in txns:
            for key in ("date", "description", "category", "amount"):
                assert key in txn, f"Missing key {key!r} in transaction {txn}"

    def test_ordered_newest_first(self, db_path):
        txns = get_recent_transactions(1)
        dates = [t["date"] for t in txns]
        assert dates == sorted(dates, reverse=True), "Transactions not ordered newest-first"

    def test_respects_limit(self, db_path):
        txns = get_recent_transactions(1, limit=3)
        assert len(txns) == 3

    def test_unknown_user_returns_empty_list(self, db_path):
        assert get_recent_transactions(9999) == []


# ------------------------------------------------------------------ #
# Unit tests — get_category_breakdown                                 #
# ------------------------------------------------------------------ #

class TestGetCategoryBreakdown:
    def test_returns_seven_categories(self, db_path):
        result = get_category_breakdown(1)
        # 7 distinct categories in seed data
        assert len(result) == 7

    def test_ordered_by_amount_descending(self, db_path):
        result = get_category_breakdown(1)
        amounts = [c["amount"] for c in result]
        assert amounts == sorted(amounts, reverse=True)

    def test_pct_sums_to_100(self, db_path):
        result = get_category_breakdown(1)
        total_pct = sum(c["pct"] for c in result)
        assert abs(total_pct - 100) < 0.5, f"pct values sum to {total_pct}, expected ~100"

    def test_items_have_required_keys(self, db_path):
        result = get_category_breakdown(1)
        for item in result:
            for key in ("name", "amount", "pct"):
                assert key in item, f"Missing key {key!r} in {item}"

    def test_first_item_is_bills(self, db_path):
        result = get_category_breakdown(1)
        assert result[0]["name"] == "Bills"

    def test_unknown_user_returns_empty_list(self, db_path):
        assert get_category_breakdown(9999) == []


# ------------------------------------------------------------------ #
# Route tests — GET /profile                                          #
# ------------------------------------------------------------------ #

class TestProfileRoute:
    def test_unauthenticated_redirects(self, client):
        response = client.get("/profile")
        assert response.status_code == 302

    def test_unauthenticated_redirect_location(self, client):
        response = client.get("/profile")
        assert "/login" in response.headers["Location"]

    def test_authenticated_returns_200(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_authenticated_shows_name(self, auth_client):
        response = auth_client.get("/profile")
        assert b"Demo User" in response.data

    def test_authenticated_shows_email(self, auth_client):
        response = auth_client.get("/profile")
        assert b"demo@spendly.com" in response.data

    def test_authenticated_shows_rupee_symbol(self, auth_client):
        response = auth_client.get("/profile")
        assert "₹".encode() in response.data
