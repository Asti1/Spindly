# Spec: Login and Logout

## Overview

This step implements session-based login and logout for Spendly. A registered
user submits their email and password; the server verifies the credentials,
starts a Flask session, and redirects them to their profile page. The logout
route clears the session and redirects to the landing page. This is the
authentication gate that all future protected routes will depend on.

## Depends on

- Step 01 — Database Setup (users table must exist)
- Step 02 — Registration (users must be creatable before they can log in)

## Routes

- `GET  /login`  — render the login form — public
- `POST /login`  — verify credentials, start session, redirect — public
- `GET  /logout` — clear session, redirect to landing — logged-in

## Database changes

No database changes. The existing `users` table with `email` and
`password_hash` columns is sufficient.

## Templates

- **Modify:** `templates/login.html` — add POST form with email and password
  fields, inline error display, and a link to `/register`. Repopulate email on
  failed login.

## Files to change

- `app.py` — convert `GET /login` stub to a two-method route with credential
  verification and session management; implement `GET /logout` to clear the
  session.

## Files to create

No new files required. `database/users.py` already provides
`get_user_by_email`.

## New dependencies

No new dependencies. `flask.session` and
`werkzeug.security.check_password_hash` are already available.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` and `user_name` in the session (never the password hash)
- Set `app.secret_key` — use a hard-coded dev string (e.g. `"spendly-dev-secret"`)
- On failed login show a single generic error: "Invalid email or password"
  (do not reveal whether the email exists)
- Strip whitespace from email before lookup
- After successful login redirect to `url_for('profile')`
- After logout redirect to `url_for('landing')`

## Definition of done

- [ ] Visiting `/login` renders the login form
- [ ] Submitting valid credentials starts a session and redirects to `/profile`
- [ ] Submitting an unrecognised email shows "Invalid email or password"
- [ ] Submitting a wrong password shows "Invalid email or password"
- [ ] After a failed login the email field retains its value
- [ ] Visiting `/logout` clears the session and redirects to `/`
- [ ] After logout, revisiting `/login` shows the empty form (no session data)
- [ ] `session['user_id']` and `session['user_name']` are set after login
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
