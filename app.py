"""Flask application for the Monthly Budget Dashboard."""

import json
import os
from flask import Flask, render_template, request, jsonify, session

from parser import parse_statement
from recommender import generate_recommendations

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Store data in memory for the session (simple approach, no database needed)
_store = {"transactions": [], "income": 0, "goals": []}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_statement():
    """Handle CSV file upload and parse transactions."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a CSV file"}), 400

    content = file.read().decode("utf-8", errors="replace")
    transactions = parse_statement(content, file.filename)

    if not transactions:
        return jsonify({"error": "No transactions found. Check that your CSV has Date, Description, and Amount columns."}), 400

    # Append to existing transactions (allows uploading multiple statements)
    _store["transactions"].extend(transactions)

    return jsonify({
        "message": f"Parsed {len(transactions)} transactions from {file.filename}",
        "new_count": len(transactions),
        "total_count": len(_store['transactions']),
        "transactions": _store["transactions"],
    })


@app.route("/transactions", methods=["GET"])
def get_transactions():
    """Return all uploaded transactions."""
    return jsonify({"transactions": _store["transactions"]})


@app.route("/clear", methods=["POST"])
def clear_data():
    """Clear all uploaded data."""
    _store["transactions"] = []
    _store["income"] = 0
    _store["goals"] = []
    return jsonify({"message": "All data cleared"})


@app.route("/analyze", methods=["POST"])
def analyze():
    """Run budget analysis with income and goals."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    income = data.get("income", 0)
    goals = data.get("goals", [])
    month = data.get("month")  # Optional: "YYYY-MM" or "all"

    try:
        income = float(income)
    except (ValueError, TypeError):
        return jsonify({"error": "Income must be a number"}), 400

    if income <= 0:
        return jsonify({"error": "Please enter a positive monthly income"}), 400

    if not _store["transactions"]:
        return jsonify({"error": "No transactions uploaded yet. Please upload a statement first."}), 400

    _store["income"] = income
    _store["goals"] = goals

    # Collect available months from all transactions
    available_months = sorted(set(
        t["date"][:7] for t in _store["transactions"] if t.get("date") and len(t["date"]) >= 7
    ))

    # Filter transactions by month if specified
    if month and month != "all":
        filtered = [t for t in _store["transactions"] if t.get("date", "").startswith(month)]
    else:
        filtered = _store["transactions"]

    if not filtered:
        return jsonify({"error": f"No transactions found for {month}."}), 400

    result = generate_recommendations(filtered, income, goals)
    result["available_months"] = available_months
    result["selected_month"] = month or "all"
    return jsonify(result)


@app.route("/update-category", methods=["POST"])
def update_category():
    """Allow manual category override for a transaction."""
    data = request.get_json()
    index = data.get("index")
    new_category = data.get("category")

    if index is None or new_category is None:
        return jsonify({"error": "Missing index or category"}), 400

    if 0 <= index < len(_store["transactions"]):
        _store["transactions"][index]["category"] = new_category
        return jsonify({"message": "Category updated", "transaction": _store["transactions"][index]})

    return jsonify({"error": "Invalid transaction index"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
