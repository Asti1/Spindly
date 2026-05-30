# Spec: Registration

## Overview

This step implements user registration for Spendly. A visitor fills out the
sign-up form (name, email, password), the server validates the input, hashes
the password, and inserts the new user into the database. On success the user
is redirected to the login page. On failure the form re-renders with a
descriptive inline error message.

## Depends on

- Step 01 — Database Setup (users table must exist)

## Routes

- `GET  /register` — render the registration form — public
- `POST /register` — process the form, create the account — public

## Database changes

No new tables or columns. The existing `users` table
(`id`, `name`, `email`, `password_hash`, `created_at`) is sufficient.

## Templates

- **Modify:** `templates/register.html` — the form already exists; ensure it
  passes `error` into the template and repopulates `name` and `email` fields
  after a failed submission so the user does not have to retype them.

## Files to change

- `app.py` — convert the `GET /register` stub into a proper two-method route
  that handles form validation and database insertion.
- `templates/register.html` — add `value` attributes to name/email inputs so
  they repopulate on error; no structural changes required.

## Files to create

- `database/users.py` — data-access functions for the users table:
  - `get_user_by_email(email)` — returns a Row or None
  - `create_user(name, email, password)` — hashes the password and inserts;
    returns the new user id

## New dependencies

No new dependencies. `werkzeug.security.generate_password_hash` is already
available via Flask.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validation order: name not blank → email not blank → email not already taken
  → password at least 8 characters
- Redirect to `url_for('login')` on success; do not log the user in
  automatically (that is Step 3)
- Strip whitespace from name and email before validation and insertion

## Definition of done

- [ ] Visiting `/register` renders the form without errors
- [ ] Submitting the form with all valid fields creates a row in `users` and
      redirects to `/login`
- [ ] Submitting with a blank name shows "Name is required"
- [ ] Submitting with a blank email shows "Email is required"
- [ ] Submitting with an already-registered email shows "An account with that email already exists"
- [ ] Submitting with a password shorter than 8 characters shows "Password must be at least 8 characters"
- [ ] After a failed submission the name and email fields retain their values
- [ ] The new user's password is stored as a hash, not plain text (verify in
      the SQLite file with `sqlite3 expense_tracker.db "SELECT password_hash FROM users LIMIT 3"`)
