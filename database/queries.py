from datetime import datetime
from database.db import get_db


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


def get_summary_stats(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT SUM(amount) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        total = row["total"] or 0
        count = row["cnt"] or 0
        if count == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
        return {
            "total_spent": float(total),
            "transaction_count": int(count),
            "top_category": top_category,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, date, description, category, amount FROM expenses"
            " WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category AS name, SUM(amount) AS amount FROM expenses"
            " WHERE user_id = ? GROUP BY category ORDER BY amount DESC",
            (user_id,)
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
        # Adjust the largest category so all pct values sum exactly to 100
        pct_sum = sum(item["pct"] for item in result)
        result[0]["pct"] += 100 - pct_sum
        return result
    finally:
        conn.close()
