from datetime import datetime
from database.db import get_db


def _date_filters(from_date, to_date):
    clauses, params = [], []
    if from_date:
        clauses.append("date >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("date <= ?")
        params.append(to_date)
    return clauses, params


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "member_since": datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y"),
        }
    finally:
        conn.close()


def get_summary_stats(user_id, from_date=None, to_date=None):
    conn = get_db()
    try:
        extra_clauses, extra_params = _date_filters(from_date, to_date)
        where = "WHERE user_id = ?"
        if extra_clauses:
            where += " AND " + " AND ".join(extra_clauses)
        params = (user_id, *extra_params)

        row = conn.execute(
            f"SELECT SUM(amount) AS total, COUNT(*) AS cnt FROM expenses {where}",
            params
        ).fetchone()
        total = row["total"] or 0
        count = row["cnt"] or 0
        if count == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        top_row = conn.execute(
            f"SELECT category FROM expenses {where} GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
        return {
            "total_spent": float(total),
            "transaction_count": int(count),
            "top_category": top_category,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10, from_date=None, to_date=None):
    conn = get_db()
    try:
        extra_clauses, extra_params = _date_filters(from_date, to_date)
        where = "WHERE user_id = ?"
        if extra_clauses:
            where += " AND " + " AND ".join(extra_clauses)
        params = (user_id, *extra_params, limit)

        rows = conn.execute(
            f"SELECT id, date, description, category, amount FROM expenses"
            f" {where} ORDER BY date DESC LIMIT ?",
            params
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id, from_date=None, to_date=None):
    conn = get_db()
    try:
        extra_clauses, extra_params = _date_filters(from_date, to_date)
        where = "WHERE user_id = ?"
        if extra_clauses:
            where += " AND " + " AND ".join(extra_clauses)
        params = (user_id, *extra_params)

        rows = conn.execute(
            f"SELECT category AS name, SUM(amount) AS amount FROM expenses"
            f" {where} GROUP BY category ORDER BY amount DESC",
            params
        ).fetchall()
        if not rows:
            return []
        total = sum(row["amount"] for row in rows)
        result = []
        for row in rows:
            result.append({
                "name": row["name"],
                "amount": float(row["amount"]),
                "pct": round(row["amount"] / total * 100),
            })
        pct_sum = sum(item["pct"] for item in result)
        result[0]["pct"] += 100 - pct_sum
        return result
    finally:
        conn.close()
