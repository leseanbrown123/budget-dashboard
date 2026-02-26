"""Credit card statement parser with automatic transaction categorization."""

import csv
import io
import re
from datetime import datetime

# Descriptions that represent payments (not expenses) and should be excluded
PAYMENT_KEYWORDS = [
    "mobile payment - thank you",
    "payment thank you",
    "online payment thank you",
    "autopay payment - thank you",
]

# Keyword-to-category mapping for auto-categorization
CATEGORY_KEYWORDS = {
    "Groceries": [
        "grocery", "groceries", "whole foods", "trader joe", "safeway",
        "kroger", "aldi", "costco", "walmart supercenter", "publix",
        "wegmans", "heb", "sprouts", "food lion", "giant", "meijer",
        "market basket", "stop & shop", "albertsons", "piggly wiggly",
    ],
    "Food Delivery": [
        "uber eats", "ubereats", "doordash", "door dash", "grubhub",
        "postmates", "seamless", "instacart", "gopuff", "caviar",
        "delivery.com", "eat24", "bite squad", "waitr", "favor delivery",
    ],
    "Dining": [
        "restaurant", "mcdonald", "starbucks", "chipotle", "subway",
        "domino", "pizza", "burger", "taco bell", "chick-fil-a",
        "wendy", "dunkin", "panera",
        "cafe", "diner", "grill", "sushi",
        "thai", "chinese", "mexican", "italian", "bar ", "pub ",
        "brewhouse", "coffee", "bakery", "deli",
    ],
    "Transportation": [
        "gas", "shell", "chevron", "exxon", "bp ", "mobil", "sunoco",
        "fuel", "uber", "lyft", "taxi", "parking", "toll", "transit",
        "metro", "bus", "train", "amtrak", "auto", "car wash",
        "jiffy lube", "valvoline", "tire",
    ],
    "Shopping": [
        "amazon", "target", "walmart", "best buy", "ebay", "etsy",
        "nordstrom", "macy", "kohls", "tj maxx", "marshalls",
        "ross", "old navy", "gap", "h&m", "zara", "nike", "adidas",
        "apple store", "ikea", "home depot", "lowes", "wayfair",
    ],
    "Entertainment": [
        "netflix", "hulu", "disney+", "spotify", "apple music",
        "youtube", "hbo", "movie", "cinema", "theater", "concert",
        "ticketmaster", "stubhub", "amc", "regal", "gaming",
        "steam", "playstation", "xbox", "nintendo", "twitch",
    ],
    "Utilities": [
        "electric", "power", "water", "gas bill", "internet",
        "comcast", "verizon", "at&t", "t-mobile", "sprint",
        "phone bill", "cable", "utility", "sewage", "trash",
    ],
    "Healthcare": [
        "pharmacy", "cvs", "walgreens", "rite aid", "hospital",
        "doctor", "dental", "dentist", "optometrist", "vision",
        "medical", "health", "clinic", "urgent care", "lab",
        "prescription", "therapy", "insurance premium",
    ],
    "Travel": [
        "airline", "delta", "united", "american airlines", "southwest",
        "jetblue", "spirit", "frontier", "hotel", "marriott", "hilton",
        "hyatt", "airbnb", "vrbo", "booking.com", "expedia",
        "travelocity", "kayak", "rental car", "hertz", "enterprise",
    ],
    "Subscriptions": [
        "subscription", "membership", "monthly", "annual fee",
        "amazon prime", "gym", "planet fitness", "la fitness",
        "ymca", "adobe", "microsoft 365", "icloud", "dropbox",
        "patreon", "substack",
    ],
    "Education": [
        "tuition", "university", "college", "school", "course",
        "udemy", "coursera", "skillshare", "textbook", "book",
        "barnes & noble", "library",
    ],
    "Personal Care": [
        "salon", "barber", "spa", "nail", "beauty", "sephora",
        "ulta", "bath & body", "hair", "skincare", "cosmetic",
    ],
    "Home": [
        "rent", "mortgage", "hoa", "property tax", "home insurance",
        "furniture", "appliance", "plumber", "electrician",
        "cleaning", "lawn", "garden",
    ],
    "Insurance": [
        "insurance", "geico", "state farm", "allstate", "progressive",
        "liberty mutual",
    ],
}

# Common date formats found in credit card statements
DATE_FORMATS = [
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d",
]


def categorize_transaction(description):
    """Assign a category to a transaction based on its description."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    return "Other"


def parse_date(date_str):
    """Try multiple date formats to parse a date string."""
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_amount(amount_str):
    """Parse an amount string, handling various formats like $1,234.56 or (100.00)."""
    s = amount_str.strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").strip()
    if s.startswith("-"):
        negative = not negative
        s = s[1:]
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def detect_columns(headers):
    """Auto-detect which columns contain date, description, and amount."""
    date_col = None
    desc_col = None
    amount_col = None
    category_col = None

    headers_lower = [h.lower().strip() for h in headers]

    for i, h in enumerate(headers_lower):
        if date_col is None and any(
            k in h for k in ["date", "trans date", "transaction date", "post date"]
        ):
            date_col = i
        elif category_col is None and any(k in h for k in ["category", "type"]):
            category_col = i
        elif desc_col is None and any(
            k in h
            for k in ["description", "merchant", "name", "memo", "details", "payee"]
        ):
            desc_col = i
        elif amount_col is None and any(
            k in h for k in ["amount", "charge", "debit", "total", "price"]
        ):
            amount_col = i

    # Fallback: assume first=date, second=description, last=amount
    if date_col is None:
        date_col = 0
    if desc_col is None:
        desc_col = 1
    if amount_col is None:
        amount_col = len(headers) - 1

    return date_col, desc_col, amount_col, category_col


def parse_statement(file_content, filename=""):
    """Parse a CSV credit card statement and return categorized transactions.

    Returns a list of dicts with keys: date, description, amount, category, flagged
    """
    transactions = []

    # Detect encoding and normalize line endings
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8", errors="replace")
    file_content = file_content.replace("\r\n", "\n").replace("\r", "\n")

    reader = csv.reader(io.StringIO(file_content))
    rows = list(reader)

    if len(rows) < 2:
        return []

    headers = rows[0]
    date_col, desc_col, amount_col, category_col = detect_columns(headers)

    for row in rows[1:]:
        if len(row) <= max(date_col, desc_col, amount_col):
            continue

        date = parse_date(row[date_col])
        description = row[desc_col].strip()
        amount = parse_amount(row[amount_col])

        if amount is None or not description:
            continue

        # Skip payment transactions (not actual expenses)
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in PAYMENT_KEYWORDS):
            continue

        # Use provided category or auto-detect
        if category_col is not None and category_col < len(row) and row[category_col].strip():
            category = row[category_col].strip()
        else:
            category = categorize_transaction(description)

        # Treat amounts as positive spending (many statements use positive = charge)
        spend_amount = abs(amount)

        transactions.append(
            {
                "date": date.strftime("%Y-%m-%d") if date else "",
                "description": description,
                "amount": round(spend_amount, 2),
                "category": category,
                "flagged": spend_amount >= 200,
            }
        )

    return transactions
