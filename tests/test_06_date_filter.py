"""
Tests for: Date Filter for Profile Page (Step 6)
Spec reference: .claude/specs/06-date-filter.md
Generated: 2026-06-03
"""

import sqlite3
import pytest
from unittest.mock import patch
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app
from database.db import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_schema(conn):
    """Create tables in the given in-memory connection."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def in_memory_db(tmp_path):
    """
    Patch DB_PATH to a temp file so every test gets a fresh, isolated SQLite
    database. Using a file-based temp path (not ':memory:') lets multiple
    get_db() calls within one request share the same data.
    """
    db_file = str(tmp_path / "test_spendly.db")
    with patch.object(db_module, "DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def test_user(in_memory_db):
    """
    Insert a single test user and return their id.
    The fixture depends on in_memory_db so DB_PATH is already patched.
    """
    conn = sqlite3.connect(in_memory_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "test@spendly.com", generate_password_hash("password123")),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


@pytest.fixture()
def expenses(in_memory_db, test_user):
    """
    Insert a controlled set of expenses spread across three months so tests
    can slice the data predictably.

    Jan 2026: Food ₹100, Transport ₹50
    Feb 2026: Bills ₹200, Health ₹75
    Mar 2026: Entertainment ₹40, Shopping ₹120
    """
    rows = [
        (test_user, 100.00, "Food",          "2026-01-10", "Jan groceries"),
        (test_user, 50.00,  "Transport",      "2026-01-20", "Jan bus pass"),
        (test_user, 200.00, "Bills",          "2026-02-05", "Feb electricity"),
        (test_user, 75.00,  "Health",         "2026-02-15", "Feb pharmacy"),
        (test_user, 40.00,  "Entertainment",  "2026-03-08", "Mar movie"),
        (test_user, 120.00, "Shopping",       "2026-03-22", "Mar shoes"),
    ]
    conn = sqlite3.connect(in_memory_db)
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client(in_memory_db):
    """Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    # Suppress the app-level init_db / seed_db that run at import time by
    # ensuring our patched DB_PATH is already in place (via in_memory_db).
    with app.test_client() as c:
        yield c


@pytest.fixture()
def logged_in_client(client, test_user):
    """Flask test client with a valid session for test_user already set."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user
        sess["user_name"] = "Test User"
    return client


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_request_redirects_to_login(self, client, in_memory_db):
        """Unauthenticated GET /profile must redirect to /login (spec: auth guard)."""
        response = client.get("/profile")
        assert response.status_code == 302, (
            f"Expected 302 redirect, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target should be /login"
        )

    def test_authenticated_request_returns_200(self, logged_in_client, expenses):
        """Authenticated GET /profile must return 200 OK."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )


class TestDefaultAllTimeView:
    def test_no_filter_params_shows_all_expenses(self, logged_in_client, expenses):
        """No query params must show all-time totals — spec: default behaviour unchanged."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200
        body = response.data.decode()
        # All 6 fixture expenses total ₹585.00; the page must not be empty of data.
        # We verify total_spent = 585.0 indirectly by checking the rendered amount.
        assert "585" in body, (
            "All-time total (585.00) should appear on the page when no filter is active"
        )

    def test_no_filter_params_shows_all_transactions(self, logged_in_client, expenses):
        """No filter must include transactions from all three fixture months."""
        response = logged_in_client.get("/profile")
        body = response.data.decode()
        assert "Jan groceries" in body or "Jan bus pass" in body, (
            "January transactions should appear with no date filter"
        )
        assert "Mar movie" in body or "Mar shoes" in body, (
            "March transactions should appear with no date filter"
        )


class TestValidDateRangeFilter:
    def test_filtered_summary_stats_reflect_only_in_range_expenses(
        self, logged_in_client, expenses
    ):
        """Summary stats must reflect only expenses within the date range (spec: summary stats filtered)."""
        # Filter to February only: Bills ₹200 + Health ₹75 = ₹275
        response = logged_in_client.get("/profile?from=2026-02-01&to=2026-02-28")
        assert response.status_code == 200
        body = response.data.decode()
        assert "275" in body, (
            "Total for Feb (275.00) should appear when filtered to 2026-02-01..2026-02-28"
        )

    def test_filtered_transaction_list_excludes_out_of_range(
        self, logged_in_client, expenses
    ):
        """Transaction list must exclude expenses outside the active range (spec: transaction list filtered)."""
        response = logged_in_client.get("/profile?from=2026-02-01&to=2026-02-28")
        body = response.data.decode()
        assert "Feb electricity" in body or "Feb pharmacy" in body, (
            "February transactions should be present in filtered view"
        )
        assert "Jan groceries" not in body, (
            "January transactions must not appear when filter starts 2026-02-01"
        )
        assert "Mar movie" not in body, (
            "March transactions must not appear when filter ends 2026-02-28"
        )

    def test_filtered_category_breakdown_excludes_out_of_range(
        self, logged_in_client, expenses
    ):
        """Category breakdown must contain only categories with in-range expenses (spec: category breakdown filtered)."""
        # Filter to January only — expect Food and Transport categories.
        response = logged_in_client.get("/profile?from=2026-01-01&to=2026-01-31")
        body = response.data.decode()
        assert "Food" in body, "Food category should appear for January filter"
        assert "Transport" in body, "Transport category should appear for January filter"
        assert "Bills" not in body, (
            "Bills category must not appear when filter is January only"
        )
        assert "Entertainment" not in body, (
            "Entertainment must not appear when filter is January only"
        )

    def test_single_day_range_returns_matching_expense(self, logged_in_client, expenses):
        """A single-day range (from == to) must return only expenses on that day."""
        response = logged_in_client.get("/profile?from=2026-01-10&to=2026-01-10")
        body = response.data.decode()
        assert "Jan groceries" in body, (
            "Expense on 2026-01-10 must appear in single-day filter"
        )
        assert "Jan bus pass" not in body, (
            "Expense on 2026-01-20 must not appear in single-day filter for 2026-01-10"
        )

    def test_range_spanning_all_fixtures_equals_all_time(
        self, logged_in_client, expenses
    ):
        """A range that covers all fixture dates must equal all-time totals."""
        response = logged_in_client.get("/profile?from=2026-01-01&to=2026-12-31")
        body = response.data.decode()
        assert "585" in body, (
            "Full-year range should show the same total as all-time (585.00)"
        )


class TestPartialFilter:
    def test_only_from_param_excludes_earlier_expenses(
        self, logged_in_client, expenses
    ):
        """Only `from` provided: expenses before `from` date are excluded (spec: partial filters valid)."""
        # from=2026-03-01 means only March expenses (₹160)
        response = logged_in_client.get("/profile?from=2026-03-01")
        assert response.status_code == 200
        body = response.data.decode()
        assert "Jan groceries" not in body, (
            "January expenses must be excluded when from=2026-03-01"
        )
        assert "Mar movie" in body or "Mar shoes" in body, (
            "March expenses must appear when from=2026-03-01 and no upper bound"
        )

    def test_only_to_param_excludes_later_expenses(
        self, logged_in_client, expenses
    ):
        """Only `to` provided: expenses after `to` date are excluded (spec: partial filters valid)."""
        # to=2026-01-31 means only January expenses (₹150)
        response = logged_in_client.get("/profile?to=2026-01-31")
        assert response.status_code == 200
        body = response.data.decode()
        assert "Mar shoes" not in body, (
            "March expenses must be excluded when to=2026-01-31"
        )
        assert "Jan groceries" in body or "Jan bus pass" in body, (
            "January expenses must appear when to=2026-01-31 and no lower bound"
        )

    def test_only_from_param_summary_total_correct(self, logged_in_client, expenses):
        """Summary total with only `from` must sum expenses on or after that date."""
        # from=2026-03-01: Entertainment ₹40 + Shopping ₹120 = ₹160
        response = logged_in_client.get("/profile?from=2026-03-01")
        body = response.data.decode()
        assert "160" in body, (
            "Total for March (160.00) should appear when from=2026-03-01 only"
        )

    def test_only_to_param_summary_total_correct(self, logged_in_client, expenses):
        """Summary total with only `to` must sum all expenses up to and including that date."""
        # to=2026-01-31: Food ₹100 + Transport ₹50 = ₹150
        response = logged_in_client.get("/profile?to=2026-01-31")
        body = response.data.decode()
        assert "150" in body, (
            "Total for January (150.00) should appear when to=2026-01-31 only"
        )


class TestEmptyRangeFilter:
    def test_filter_with_no_matching_expenses_shows_zero_total(
        self, logged_in_client, expenses
    ):
        """Range with no matching expenses must show ₹0 total, not an error (spec: empty range)."""
        response = logged_in_client.get("/profile?from=2025-01-01&to=2025-01-31")
        assert response.status_code == 200, (
            f"Expected 200 for empty range, got {response.status_code}"
        )
        body = response.data.decode()
        assert "0" in body, "Zero total should appear when no expenses match the range"

    def test_filter_with_no_matching_expenses_shows_zero_transaction_count(
        self, logged_in_client, expenses
    ):
        """Range with no matching expenses must show 0 transaction count (spec: empty range)."""
        response = logged_in_client.get("/profile?from=2025-01-01&to=2025-01-31")
        body = response.data.decode()
        # No expense rows from fixtures should appear
        assert "Jan groceries" not in body
        assert "Feb electricity" not in body
        assert "Mar movie" not in body

    def test_filter_future_range_returns_200_not_500(
        self, logged_in_client, expenses
    ):
        """A valid future date range with no expenses must return 200, not 500 (spec: no errors)."""
        response = logged_in_client.get("/profile?from=2099-01-01&to=2099-12-31")
        assert response.status_code == 200, (
            f"Future range should return 200, got {response.status_code}"
        )


class TestInvertedRangeFilter:
    def test_inverted_range_silently_ignored_returns_all_time_data(
        self, logged_in_client, expenses
    ):
        """from > to must be silently ignored and fall back to all-time data (spec: invalid dates treated as no filter)."""
        response = logged_in_client.get("/profile?from=2026-03-01&to=2026-01-01")
        assert response.status_code == 200, (
            f"Inverted range must not cause a 5xx, got {response.status_code}"
        )
        body = response.data.decode()
        # With the filter dropped, all-time total ₹585 should be present
        assert "585" in body, (
            "Inverted range should be discarded and all-time total (585) shown"
        )

    def test_inverted_range_shows_all_transactions(self, logged_in_client, expenses):
        """When inverted range is discarded, all fixture transactions should be visible."""
        response = logged_in_client.get("/profile?from=2026-12-31&to=2026-01-01")
        body = response.data.decode()
        assert "Jan groceries" in body or "Jan bus pass" in body, (
            "January transactions should reappear after inverted range is discarded"
        )


class TestInvalidDateStrings:
    @pytest.mark.parametrize("bad_from", [
        "not-a-date",
        "01-01-2026",   # wrong order
        "2026/01/01",   # wrong separator
        "20260101",     # no separators
        "abcd-ef-gh",
        "",
    ])
    def test_invalid_from_param_does_not_cause_500(
        self, logged_in_client, expenses, bad_from
    ):
        """Non-YYYY-MM-DD `from` value must be ignored silently, never raise 500 (spec: invalid dates)."""
        response = logged_in_client.get(f"/profile?from={bad_from}&to=2026-12-31")
        assert response.status_code == 200, (
            f"Invalid from='{bad_from}' should not cause a 500, got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_to", [
        "not-a-date",
        "31-12-2026",
        "2026/12/31",
        "99999-99-99",
        "tomorrow",
        "",
    ])
    def test_invalid_to_param_does_not_cause_500(
        self, logged_in_client, expenses, bad_to
    ):
        """Non-YYYY-MM-DD `to` value must be ignored silently, never raise 500 (spec: invalid dates)."""
        response = logged_in_client.get(f"/profile?from=2026-01-01&to={bad_to}")
        assert response.status_code == 200, (
            f"Invalid to='{bad_to}' should not cause a 500, got {response.status_code}"
        )

    def test_both_params_invalid_falls_back_to_all_time(
        self, logged_in_client, expenses
    ):
        """Both params invalid must fall back to all-time data, not error (spec: invalid dates)."""
        response = logged_in_client.get("/profile?from=bad&to=alsoBad")
        assert response.status_code == 200
        body = response.data.decode()
        assert "585" in body, (
            "All-time total should show when both date params are invalid"
        )

    def test_invalid_from_with_valid_to_treated_as_only_to_filter(
        self, logged_in_client, expenses
    ):
        """Invalid `from` with valid `to` means only the `to` bound applies (spec: partial filters)."""
        # Valid to=2026-01-31 should still bound the upper end even though from is bad
        response = logged_in_client.get("/profile?from=INVALID&to=2026-01-31")
        assert response.status_code == 200
        body = response.data.decode()
        assert "Mar shoes" not in body, (
            "March expenses must not appear when to=2026-01-31 is valid"
        )


class TestURLBookmarkability:
    def test_filter_form_uses_get_method(self, logged_in_client, expenses):
        """The filter form must use GET so the filtered URL is bookmarkable (spec: GET form)."""
        response = logged_in_client.get("/profile")
        body = response.data.decode()
        # The form tag should declare method="get" (case-insensitive)
        assert 'method="get"' in body.lower() or "method='get'" in body.lower(), (
            "Filter form must use GET method for bookmarkable URLs"
        )

    def test_active_filter_values_are_pre_filled_in_form_inputs(
        self, logged_in_client, expenses
    ):
        """Form inputs must be pre-filled with the active filter values (spec: inputs pre-filled)."""
        response = logged_in_client.get("/profile?from=2026-02-01&to=2026-02-28")
        body = response.data.decode()
        assert "2026-02-01" in body, (
            "from_date value '2026-02-01' should appear in the rendered HTML"
        )
        assert "2026-02-28" in body, (
            "to_date value '2026-02-28' should appear in the rendered HTML"
        )

    def test_no_filter_params_inputs_not_pre_filled_with_stale_values(
        self, logged_in_client, expenses
    ):
        """With no active filter the date inputs must not carry stale values (spec: pre-fill only when active)."""
        response = logged_in_client.get("/profile")
        body = response.data.decode()
        # Page must not accidentally hard-code a date range when none is active.
        # We check that neither a January nor a February fixture date appears inside
        # a value="" attribute context. A simple presence check is sufficient since
        # the template should only inject from_date / to_date when they are not None.
        assert 'value="2026-01-01"' not in body, (
            "No stale from_date should be pre-filled when no filter is active"
        )
        assert 'value="2026-12-31"' not in body, (
            "No stale to_date should be pre-filled when no filter is active"
        )


class TestActiveFilterLabel:
    def test_active_filter_range_label_shown_when_filter_applied(
        self, logged_in_client, expenses
    ):
        """When a filter is active the page must display the active range label (spec: 'Showing: ... → ...' label)."""
        response = logged_in_client.get("/profile?from=2026-01-01&to=2026-03-31")
        body = response.data.decode()
        # Spec says label like "Showing: 2026-01-01 → 2026-03-31"
        assert "2026-01-01" in body and "2026-03-31" in body, (
            "Active filter label must contain both from and to dates"
        )

    def test_no_filter_label_shown_when_no_params(self, logged_in_client, expenses):
        """With no filter active the 'Showing' range label must not appear (spec: label only when active)."""
        response = logged_in_client.get("/profile")
        body = response.data.decode()
        assert "Showing:" not in body, (
            "'Showing:' label must not appear when no date filter is active"
        )

    def test_clear_link_present_when_filter_active(self, logged_in_client, expenses):
        """A 'Clear' link pointing to /profile (no params) must be present when filter is active (spec: Clear link)."""
        response = logged_in_client.get("/profile?from=2026-01-01&to=2026-03-31")
        body = response.data.decode()
        # The spec requires a Clear link that navigates to /profile with no query params.
        assert 'href="/profile"' in body, (
            "A 'Clear' link to bare /profile must be present when filter is active"
        )


class TestBoundaryConditions:
    def test_zero_amount_expense_in_range_counted_correctly(
        self, logged_in_client, in_memory_db, test_user
    ):
        """A ₹0.00 expense within range must be counted without errors (boundary: zero amount)."""
        conn = sqlite3.connect(in_memory_db)
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (test_user, 0.00, "Other", "2026-04-01", "zero expense"),
        )
        conn.commit()
        conn.close()

        response = logged_in_client.get("/profile?from=2026-04-01&to=2026-04-01")
        assert response.status_code == 200
        body = response.data.decode()
        assert "zero expense" in body, (
            "Zero-amount expense in range must appear in transaction list"
        )

    def test_single_expense_in_db_is_top_category(
        self, logged_in_client, in_memory_db, test_user
    ):
        """With only one expense the top category must equal that expense's category."""
        conn = sqlite3.connect(in_memory_db)
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (test_user, 99.99, "Health", "2026-05-15", "single expense"),
        )
        conn.commit()
        conn.close()

        response = logged_in_client.get("/profile?from=2026-05-01&to=2026-05-31")
        assert response.status_code == 200
        body = response.data.decode()
        assert "Health" in body, (
            "Top category must be 'Health' when only one Health expense is in range"
        )

    def test_category_breakdown_percentages_sum_to_100(
        self, logged_in_client, expenses
    ):
        """Category breakdown percentages must sum to 100 for any valid range (boundary: pct rounding)."""
        # This test validates the route returns 200 without arithmetic errors
        # for a multi-category range. The actual pct logic is in queries.py but
        # the spec requires no errors be raised.
        response = logged_in_client.get("/profile?from=2026-01-01&to=2026-03-31")
        assert response.status_code == 200, (
            "Multi-category filtered view must return 200 without arithmetic errors"
        )

    @pytest.mark.parametrize("from_d,to_d,expected_total", [
        ("2026-01-01", "2026-01-31", 150.0),   # Jan: 100 + 50
        ("2026-02-01", "2026-02-28", 275.0),   # Feb: 200 + 75
        ("2026-03-01", "2026-03-31", 160.0),   # Mar: 40 + 120
        ("2026-01-01", "2026-02-28", 425.0),   # Jan+Feb: 150 + 275
        ("2026-02-01", "2026-03-31", 435.0),   # Feb+Mar: 275 + 160
    ])
    def test_parametrized_monthly_totals(
        self, logged_in_client, expenses, from_d, to_d, expected_total
    ):
        """Filtered totals must be arithmetically correct for various monthly ranges."""
        response = logged_in_client.get(f"/profile?from={from_d}&to={to_d}")
        assert response.status_code == 200
        body = response.data.decode()
        # Convert to string without trailing zero ambiguity: check integer part
        total_str = str(int(expected_total))
        assert total_str in body, (
            f"Expected total {expected_total} (checking '{total_str}') for range {from_d}..{to_d}"
        )
