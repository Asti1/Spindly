# Spec: Profile Page Design

## Overview

This step implements the `/profile` route and its template, giving logged-in
users a home base after authentication. The profile page displays the user's
name, email, and account creation date, along with a summary of their expenses
(total spend, spend by category, and a recent-expenses list). It is the first
protected route in Spendly — unauthenticated visitors are redirected to
`/login`. All subsequent feature steps (add, edit, delete expense) will link
back to this page.

## Depends on

- Step 01 — Database Setup (users and expenses tables must exist)
- Step 02 — Registration (users must be creatable)
- Step 03 — Login and Logout (session must be set before this page is reachable)

## Routes

- `GET /profile` — render the profile dashboard — logged-in only (redirect to `/login` if no session)

## Database changes

No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates

- **Create:** `templates/profile.html` — full profile/dashboard page that
  extends `base.html`. Sections:
  1. **Header** — greeting with user's name and a "Sign out" link.
  2. **Stats row** — total spend this month, number of expenses, top category.
  3. **Category breakdown** — visual bar rows (similar to the mock card on the
     landing page) showing spend per category.
  4. **Recent expenses table** — last 10 expenses (date, category, description,
     amount), with placeholder "Edit" and "Delete" links pointing to the
     not-yet-implemented routes.
  5. **Add expense CTA** — prominent button linking to `/expenses/add`.

## Files to change

- `app.py` — replace the `/profile` stub string response with a real view that:
  - Checks `session.get('user_id')`; if absent redirects to `url_for('login')`.
  - Queries the database for the logged-in user's record and their expenses.
  - Passes user data and expense summary to `render_template('profile.html')`.

## Files to create

- `templates/profile.html` — the profile/dashboard template described above.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (no changes to auth here, rule kept for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Guard the route with a session check; redirect unauthenticated users to `/login`
- Compute totals and category breakdown in Python (in `app.py`), not in the template
- Category breakdown should only list categories that have at least one expense
- Amount values displayed in Indian Rupee format: `₹ X,XXX.XX`
- The "Edit" and "Delete" links in the recent-expenses table may point to the
  existing stub routes (`/expenses/<id>/edit`, `/expenses/<id>/delete`) —
  they will be wired up in later steps
- Do not add inline styles; use or extend the existing CSS classes in `style.css`

## Definition of done

- [ ] Visiting `/profile` without a session redirects to `/login`
- [ ] After login, visiting `/profile` renders the profile page (HTTP 200)
- [ ] The page displays the logged-in user's name
- [ ] The page displays the correct total spend for the user's expenses
- [ ] The category breakdown lists every category that has at least one expense
- [ ] The recent-expenses table shows up to 10 rows ordered by date descending
- [ ] Each expense row shows date, category, description, and amount
- [ ] The "Add expense" button links to `/expenses/add`
- [ ] The navbar shows the user's name and a "Sign out" link (inherited from `base.html`)
- [ ] The demo user (`demo@spendly.com` / `demo123`) sees 8 seeded expenses on their profile
