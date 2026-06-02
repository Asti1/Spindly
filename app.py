from collections import defaultdict

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db
from database.users import create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

# Ensure the database schema and demo data are ready before serving requests.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        error = "Name is required"
    elif not email:
        error = "Email is required"
    elif get_user_by_email(email):
        error = "An account with that email already exists"
    elif len(password) < 8:
        error = "Password must be at least 8 characters"
    else:
        create_user(name, email, password)
        return redirect(url_for("login"))

    return render_template("register.html", error=error, name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password", email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        expenses = conn.execute(
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ? ORDER BY date DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    total = sum(e["amount"] for e in expenses)
    recent = expenses[:10]

    cat_totals = defaultdict(float)
    for e in expenses:
        cat_totals[e["category"]] += e["amount"]
    category_breakdown = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    top_category = category_breakdown[0][0] if category_breakdown else "—"
    max_cat_amount = category_breakdown[0][1] if category_breakdown else 1

    return render_template(
        "profile.html",
        user=user,
        total=total,
        expense_count=len(expenses),
        top_category=top_category,
        category_breakdown=category_breakdown,
        max_cat_amount=max_cat_amount,
        recent=recent,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
