# Spec: Date Filter for Profile Page

## Overview

Step 6 adds a date range filter to the profile page so users can scope all
summary stats and transaction data to a chosen time period. Currently the
profile page always shows all-time totals, which becomes less useful as
expense history grows. This step adds a simple form with "from" and "to" date
inputs; submitting it reloads `/profile` with query parameters that narrow
every data section — summary stats, recent transactions, and category
breakdown — to that window. The default view (no filter applied) continues to
show all-time data.

## Depends on

- Step 1: Database setup (`expenses` table with `date` column exists)
- Step 2: Registration (users stored in the database)
- Step 3: Login / Logout (`session["user_id"]` set on login)
- Step 4: Profile page static UI (template structure in place)
- Step 5: Backend routes (query helpers in `database/queries.py` exist)

## Routes

- `GET /profile?from=YYYY-MM-DD&to=YYYY-MM-DD` — filtered profile view — logged-in only

No new route path; the existing `GET /profile` route gains optional query
parameters `from` and `to`.

## Database changes

No database changes. The `expenses.date` column (TEXT, YYYY-MM-DD format) is
already present and sufficient for range filtering.

## Templates

- **Modify**: `templates/profile.html`
  - Add a filter form above the summary stats section with two date inputs
    (`from_date`, `to_date`) and a "Apply" submit button.
  - Add a "Clear" link that navigates to `/profile` with no query params.
  - When a filter is active, show the active range as a label (e.g.
    "Showing: 2026-01-01 → 2026-06-01").
  - All four data sections (summary stats, transactions, category breakdown)
    must reflect the filtered data, not all-time data.
  - Inputs must be pre-filled with the currently active filter values on page
    load so the user can see and adjust the active filter.

## Files to change

- `app.py` — read `from` and `to` query params in the `profile()` view and
  pass them to each query helper; pass `from_date` and `to_date` back to the
  template for pre-filling the filter form.
- `database/queries.py` — add optional `from_date` and `to_date` parameters
  to `get_summary_stats`, `get_recent_transactions`, and
  `get_category_breakdown`; when provided, add a `WHERE date BETWEEN ? AND ?`
  clause.

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- Date inputs must use `type="date"` (native browser date picker)
- If `from` or `to` is absent from the query string, treat it as no lower/upper
  bound respectively (i.e. partial filters are valid)
- Invalid date strings (non-YYYY-MM-DD, `from` > `to`) must be silently ignored
  and treated as if no filter was provided — never raise a 500
- The filter form must use GET (not POST) so the filtered URL is bookmarkable
- `get_user_by_id` does not need date filtering (user meta is not date-scoped)

## Definition of done

- [ ] Visiting `/profile` with no query params shows all-time totals (unchanged behaviour)
- [ ] Submitting the filter form with a valid date range reloads the page with
      `?from=…&to=…` in the URL
- [ ] Summary stats (total spent, transaction count, top category) reflect only
      expenses within the selected date range
- [ ] Transaction list shows only transactions within the selected date range
- [ ] Category breakdown reflects only expenses within the selected date range
- [ ] The filter form inputs are pre-filled with the active `from` / `to` values
      after filtering
- [ ] A "Clear" link resets the view to all-time data
- [ ] Filtering to a range with no expenses shows ₹0.00, 0 transactions, and an
      empty category breakdown — no errors
- [ ] An invalid date in the query string does not cause a 500 error
