import re

RULES = [
    (r"\bUPPCL\b|ELECTRICITY", "Utilities"),
    (r"ZOMATO|SWIGGY", "Food & Dining"),
    (r"D ?MART|BIGBASKET|FLIPKART|AMAZON", "Shopping / Groceries"),
    (r"JIO RECHARGE|AIRTEL", "Mobile & Recharge"),
    (r"UBER|OLA", "Transport"),
    (r"ATM/CASH WDL", "Cash Withdrawal"),
    (r"SALARY CREDIT", "Salary / Income"),
    (r"NEFT/CR|IMPS.*TRANSFER|FUNDS\s*TRANSFER", "Bank Transfer - Credit"),
    (r"UPI/DR", "UPI - Sent"),
    (r"UPI/CR", "UPI - Received"),
    (r"POS/VISA", "Card Purchase"),
]

def classify_rule_based(description: str) -> str | None:
    desc = description.upper()
    for pattern, category in RULES:
        if re.search(pattern, desc):
            return category
    return None  # unresolved -> hand off to ML model