"""Budget recommendation engine based on personal finance best practices."""


# 50/30/20 rule baseline allocations (percentage of income)
BASELINE_ALLOCATIONS = {
    "Needs": {
        "target_pct": 50,
        "categories": [
            "Groceries",
            "Utilities",
            "Transportation",
            "Healthcare",
            "Home",
            "Insurance",
        ],
    },
    "Wants": {
        "target_pct": 30,
        "categories": [
            "Dining",
            "Shopping",
            "Entertainment",
            "Subscriptions",
            "Personal Care",
            "Travel",
        ],
    },
    "Savings & Other": {
        "target_pct": 20,
        "categories": ["Education", "Other"],
    },
}

# Category-specific spending guidelines (as % of monthly income)
CATEGORY_GUIDELINES = {
    "Groceries": {"max_pct": 12, "tip": "Meal planning and buying in bulk can cut grocery costs by 20-30%."},
    "Dining": {"max_pct": 8, "tip": "Limiting dining out to 2-3 times per week can save significantly."},
    "Transportation": {"max_pct": 10, "tip": "Consider carpooling or public transit to reduce costs."},
    "Shopping": {"max_pct": 5, "tip": "Use a 48-hour rule: wait 2 days before non-essential purchases."},
    "Entertainment": {"max_pct": 5, "tip": "Look for free local events and use library resources."},
    "Utilities": {"max_pct": 8, "tip": "Smart thermostats and LED bulbs can lower utility bills 10-15%."},
    "Healthcare": {"max_pct": 8, "tip": "Use an HSA/FSA if available for tax-advantaged healthcare spending."},
    "Travel": {"max_pct": 5, "tip": "Book 3-6 months ahead and use travel rewards cards."},
    "Subscriptions": {"max_pct": 3, "tip": "Audit subscriptions quarterly; cancel anything unused for 30+ days."},
    "Personal Care": {"max_pct": 3, "tip": "Look for loyalty programs at your regular providers."},
    "Home": {"max_pct": 30, "tip": "Housing should ideally be under 30% of gross income."},
    "Insurance": {"max_pct": 10, "tip": "Bundle policies and shop around annually for better rates."},
    "Education": {"max_pct": 5, "tip": "Consider free online resources and employer tuition assistance."},
}


def classify_need_want(category):
    """Classify a spending category as Need, Want, or Savings."""
    for bucket, info in BASELINE_ALLOCATIONS.items():
        if category in info["categories"]:
            return bucket
    return "Wants"


def generate_recommendations(transactions, monthly_income, goals=None):
    """Generate budget recommendations based on transactions and user goals.

    Args:
        transactions: List of transaction dicts from parser
        monthly_income: User's monthly take-home income
        goals: Optional list of goal strings (e.g., ["Save for emergency fund", "Pay off debt"])

    Returns:
        Dict with spending analysis and recommendations
    """
    if not transactions or monthly_income <= 0:
        return {"error": "Need transactions and a positive monthly income to generate recommendations."}

    # Aggregate spending by category
    category_totals = {}
    for t in transactions:
        cat = t["category"]
        category_totals[cat] = category_totals.get(cat, 0) + t["amount"]

    total_spending = sum(category_totals.values())

    # Bucket spending into Needs / Wants / Savings
    bucket_totals = {"Needs": 0, "Wants": 0, "Savings & Other": 0}
    for cat, amount in category_totals.items():
        bucket = classify_need_want(cat)
        bucket_totals[bucket] += amount

    # Calculate percentages
    bucket_pcts = {}
    for bucket, amount in bucket_totals.items():
        bucket_pcts[bucket] = round((amount / monthly_income) * 100, 1) if monthly_income else 0

    # Category-level analysis
    category_analysis = []
    for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        pct_of_income = round((amount / monthly_income) * 100, 1)
        guideline = CATEGORY_GUIDELINES.get(cat, {"max_pct": 10, "tip": ""})
        status = "over" if pct_of_income > guideline["max_pct"] else "ok"
        category_analysis.append(
            {
                "category": cat,
                "amount": round(amount, 2),
                "pct_of_income": pct_of_income,
                "guideline_pct": guideline["max_pct"],
                "status": status,
                "tip": guideline["tip"] if status == "over" else "",
            }
        )

    # Build recommendations list
    recommendations = []

    # 50/30/20 analysis
    for bucket, info in BASELINE_ALLOCATIONS.items():
        actual_pct = bucket_pcts.get(bucket, 0)
        target_pct = info["target_pct"]
        if actual_pct > target_pct:
            over_amount = round((actual_pct - target_pct) / 100 * monthly_income, 2)
            recommendations.append(
                {
                    "type": "warning",
                    "title": f"{bucket} spending is above target",
                    "detail": (
                        f"You're spending {actual_pct}% of income on {bucket} "
                        f"(target: {target_pct}%). Consider reducing by ${over_amount:.2f}/month."
                    ),
                }
            )
        else:
            recommendations.append(
                {
                    "type": "success",
                    "title": f"{bucket} spending is on track",
                    "detail": f"{bucket} at {actual_pct}% of income (target: {target_pct}%).",
                }
            )

    # Spending rate check
    spending_pct = round((total_spending / monthly_income) * 100, 1)
    leftover = monthly_income - total_spending
    if spending_pct > 90:
        recommendations.append(
            {
                "type": "danger",
                "title": "Very little margin remaining",
                "detail": (
                    f"You've spent {spending_pct}% of your monthly income "
                    f"(${total_spending:,.2f} of ${monthly_income:,.2f}). "
                    f"Only ${leftover:,.2f} remaining for savings and unexpected costs."
                ),
            }
        )
    elif spending_pct > 80:
        recommendations.append(
            {
                "type": "warning",
                "title": "Spending approaching income limit",
                "detail": (
                    f"You've spent {spending_pct}% of your income. "
                    f"Aim to keep total spending under 80% to build savings."
                ),
            }
        )
    else:
        recommendations.append(
            {
                "type": "success",
                "title": "Good spending margin",
                "detail": (
                    f"You're spending {spending_pct}% of income, leaving "
                    f"${leftover:,.2f} for savings and investments."
                ),
            }
        )

    # Categories over guideline
    over_budget_cats = [c for c in category_analysis if c["status"] == "over"]
    for cat_info in over_budget_cats:
        recommendations.append(
            {
                "type": "warning",
                "title": f"{cat_info['category']} is over guideline",
                "detail": (
                    f"{cat_info['category']} at {cat_info['pct_of_income']}% of income "
                    f"(guideline: {cat_info['guideline_pct']}%). {cat_info['tip']}"
                ),
            }
        )

    # Goal-specific recommendations
    goal_recommendations = []
    if goals:
        for goal in goals:
            goal_lower = goal.lower()
            if any(k in goal_lower for k in ["emergency", "rainy day", "safety net"]):
                target_fund = monthly_income * 6
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            f"Target: ${target_fund:,.2f} (6 months of income). "
                            f"If you save ${leftover:,.2f}/month, you'd reach this in "
                            f"{int(target_fund / max(leftover, 1))} months. "
                            f"Consider automating transfers to a high-yield savings account."
                        ),
                    }
                )
            elif any(k in goal_lower for k in ["debt", "pay off", "loan", "credit card"]):
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            "Use the avalanche method (pay highest-interest debt first) "
                            "to minimize total interest paid. Redirect any 'Wants' savings "
                            f"toward debt. Current available: ${leftover:,.2f}/month after spending."
                        ),
                    }
                )
            elif any(k in goal_lower for k in ["save", "saving", "down payment", "house", "car"]):
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            f"With ${leftover:,.2f}/month available after spending, "
                            f"consider setting up automatic transfers. "
                            f"Cutting 'Wants' spending by 10% would free up an additional "
                            f"${bucket_totals.get('Wants', 0) * 0.1:,.2f}/month."
                        ),
                    }
                )
            elif any(k in goal_lower for k in ["retire", "retirement", "401k", "ira"]):
                target_retirement = monthly_income * 0.15
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            f"Aim to save 15% of income (${target_retirement:,.2f}/month) for retirement. "
                            f"Max out employer 401(k) match first, then consider Roth IRA. "
                            f"Current margin: ${leftover:,.2f}/month."
                        ),
                    }
                )
            elif any(k in goal_lower for k in ["invest", "stock", "portfolio"]):
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            "Ensure you have 3-6 months emergency fund before investing. "
                            "Consider low-cost index funds for long-term growth. "
                            f"Available to invest: ${leftover:,.2f}/month after expenses."
                        ),
                    }
                )
            else:
                goal_recommendations.append(
                    {
                        "type": "info",
                        "title": f"Goal: {goal}",
                        "detail": (
                            f"With ${leftover:,.2f}/month remaining after expenses, "
                            f"create a dedicated savings line for this goal. "
                            f"Automating a fixed transfer each payday helps build consistency."
                        ),
                    }
                )

    # Flagged major purchases
    flagged = [t for t in transactions if t["flagged"]]
    flagged.sort(key=lambda t: t["amount"], reverse=True)

    return {
        "total_spending": round(total_spending, 2),
        "monthly_income": monthly_income,
        "spending_pct": spending_pct,
        "remaining": round(leftover, 2),
        "bucket_totals": {k: round(v, 2) for k, v in bucket_totals.items()},
        "bucket_pcts": bucket_pcts,
        "category_analysis": category_analysis,
        "recommendations": recommendations,
        "goal_recommendations": goal_recommendations,
        "flagged_purchases": flagged,
    }
