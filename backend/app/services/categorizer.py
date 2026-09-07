CATEGORY_RULES: dict[str, list[str]] = {
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe", "food", "dominos", "mcdonald"],
    "Transport": ["uber", "ola", "rapido", "petrol", "fuel", "metro", "irctc", "fastag"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "shopping"],
    "Bills & Utilities": ["electricity", "recharge", "broadband", "jio", "airtel", "bescom", "water bill"],
    "Investments": ["zerodha", "groww", "sip", "mutual fund", "upstox", "nse", "bse"],
    "Salary & Income": ["salary", "payroll", "neft credit", "credited by"],
    "Healthcare": ["pharmacy", "hospital", "apollo", "medplus", "1mg"],
    "Entertainment": ["netflix", "spotify", "prime video", "hotstar", "bookmyshow"],
    "Rent & Housing": ["rent", "housing", "maintenance"],
}


def classify(narration: str, txn_type: str) -> str:
    text = (narration or "").lower()
    if txn_type.upper() == "CREDIT":
        for keyword in CATEGORY_RULES["Salary & Income"]:
            if keyword in text:
                return "Salary & Income"
    for category, keywords in CATEGORY_RULES.items():
        if category == "Salary & Income":
            continue
        for keyword in keywords:
            if keyword in text:
                return category
    return "Other"
