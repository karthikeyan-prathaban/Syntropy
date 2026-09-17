"""Canonical merchant alias table.

Keys are the canonical key; values carry the display name, category, and the raw
tokens (VPA handles, POS descriptors, ACH mandate names) seen in Indian narrations.
"""

MERCHANT_ALIASES: dict[str, dict] = {
    "swiggy": {
        "display": "Swiggy",
        "category": "Food & Dining",
        "tokens": ["swiggy", "bundl technologies", "swiggyupi", "swiggystores"],
    },
    "zomato": {
        "display": "Zomato",
        "category": "Food & Dining",
        "tokens": ["zomato", "zomatoltd", "zomato media"],
    },
    "blinkit": {
        "display": "Blinkit",
        "category": "Groceries",
        "tokens": ["blinkit", "grofers", "blink commerce"],
    },
    "zepto": {"display": "Zepto", "category": "Groceries", "tokens": ["zepto", "geddit convenience"]},
    "bigbasket": {"display": "BigBasket", "category": "Groceries", "tokens": ["bigbasket", "innovative retail"]},
    "amazon": {
        "display": "Amazon",
        "category": "Shopping",
        "tokens": ["amazon", "amazonpay", "amazon pay india", "amzn", "clicktech retail"],
    },
    "flipkart": {
        "display": "Flipkart",
        "category": "Shopping",
        "tokens": ["flipkart", "flipkartinternet", "fkrt"],
    },
    "myntra": {"display": "Myntra", "category": "Shopping", "tokens": ["myntra", "myntra designs"]},
    "ajio": {"display": "AJIO", "category": "Shopping", "tokens": ["ajio", "reliance retail ajio"]},
    "meesho": {"display": "Meesho", "category": "Shopping", "tokens": ["meesho", "fashnear"]},
    "uber": {"display": "Uber", "category": "Transport", "tokens": ["uber", "uberindia", "uber india systems"]},
    "ola": {"display": "Ola", "category": "Transport", "tokens": ["ola", "olacabs", "ani technologies"]},
    "rapido": {"display": "Rapido", "category": "Transport", "tokens": ["rapido", "roppen transportation"]},
    "irctc": {"display": "IRCTC", "category": "Transport", "tokens": ["irctc", "indian railway"]},
    "indianoil": {"display": "IndianOil", "category": "Transport", "tokens": ["indianoil", "iocl", "indian oil"]},
    "hpcl": {"display": "HP Petrol", "category": "Transport", "tokens": ["hpcl", "hindustan petroleum"]},
    "bpcl": {"display": "Bharat Petroleum", "category": "Transport", "tokens": ["bpcl", "bharat petroleum"]},
    "fastag": {"display": "FASTag", "category": "Transport", "tokens": ["fastag", "netc", "nhai"]},
    "netflix": {"display": "Netflix", "category": "Entertainment", "tokens": ["netflix", "netflix entertainment"]},
    "spotify": {"display": "Spotify", "category": "Entertainment", "tokens": ["spotify", "spotify india"]},
    "hotstar": {
        "display": "JioHotstar",
        "category": "Entertainment",
        "tokens": ["hotstar", "disney", "jiohotstar", "novi digital"],
    },
    "primevideo": {"display": "Prime Video", "category": "Entertainment", "tokens": ["prime video", "primevideo"]},
    "bookmyshow": {
        "display": "BookMyShow",
        "category": "Entertainment",
        "tokens": ["bookmyshow", "bigtree entertainment"],
    },
    "youtube": {"display": "YouTube Premium", "category": "Entertainment", "tokens": ["youtube", "google youtube"]},
    "jio": {"display": "Jio", "category": "Bills & Utilities", "tokens": ["jio", "reliance jio", "jio platforms"]},
    "airtel": {"display": "Airtel", "category": "Bills & Utilities", "tokens": ["airtel", "bharti airtel"]},
    "vodafoneidea": {"display": "Vi", "category": "Bills & Utilities", "tokens": ["vodafone", "vodafone idea", "vi "]},
    "bescom": {"display": "BESCOM", "category": "Bills & Utilities", "tokens": ["bescom", "bangalore electricity"]},
    "tataplay": {"display": "Tata Play", "category": "Bills & Utilities", "tokens": ["tata play", "tatasky"]},
    "actfibernet": {"display": "ACT Fibernet", "category": "Bills & Utilities", "tokens": ["act fibernet", "atria"]},
    "zerodha": {"display": "Zerodha", "category": "Investments", "tokens": ["zerodha", "zerodha broking"]},
    "groww": {"display": "Groww", "category": "Investments", "tokens": ["groww", "nextbillion technology"]},
    "upstox": {"display": "Upstox", "category": "Investments", "tokens": ["upstox", "rksv securities"]},
    "indmoney": {"display": "INDmoney", "category": "Investments", "tokens": ["indmoney", "finzoom"]},
    "kuvera": {"display": "Kuvera", "category": "Investments", "tokens": ["kuvera", "arevuk advisory"]},
    "apollopharmacy": {
        "display": "Apollo Pharmacy",
        "category": "Healthcare",
        "tokens": ["apollo pharmacy", "apollo hospitals", "apollo"],
    },
    "pharmeasy": {"display": "PharmEasy", "category": "Healthcare", "tokens": ["pharmeasy", "axelia solutions"]},
    "onemg": {"display": "Tata 1mg", "category": "Healthcare", "tokens": ["1mg", "tata 1mg", "onemg"]},
    "practo": {"display": "Practo", "category": "Healthcare", "tokens": ["practo"]},
    "cult": {"display": "Cult.fit", "category": "Healthcare", "tokens": ["cult", "cultfit", "curefit"]},
    "starbucks": {"display": "Starbucks", "category": "Food & Dining", "tokens": ["starbucks", "tata starbucks"]},
    "dominos": {"display": "Domino's", "category": "Food & Dining", "tokens": ["dominos", "jubilant foodworks"]},
    "mcdonalds": {"display": "McDonald's", "category": "Food & Dining", "tokens": ["mcdonald", "hardcastle"]},
    "kfc": {"display": "KFC", "category": "Food & Dining", "tokens": ["kfc", "devyani international"]},
    "dmart": {"display": "DMart", "category": "Groceries", "tokens": ["dmart", "avenue supermarts"]},
    "reliancefresh": {"display": "Reliance Fresh", "category": "Groceries", "tokens": ["reliance fresh", "relianceretail"]},
    "lictata": {"display": "LIC", "category": "Insurance", "tokens": ["lic of india", "lici", "life insurance corp"]},
    "hdfcergo": {"display": "HDFC ERGO", "category": "Insurance", "tokens": ["hdfc ergo", "hdfcergo"]},
    "policybazaar": {"display": "Policybazaar", "category": "Insurance", "tokens": ["policybazaar", "pb fintech"]},
    "googleplay": {"display": "Google Play", "category": "Subscriptions", "tokens": ["google play", "google india"]},
    "apple": {"display": "Apple", "category": "Subscriptions", "tokens": ["apple.com", "apple services", "itunes"]},
    "openai": {"display": "OpenAI", "category": "Subscriptions", "tokens": ["openai", "chatgpt"]},
    "adobe": {"display": "Adobe", "category": "Subscriptions", "tokens": ["adobe", "adobe systems"]},
}

# Reverse index built once: token -> canonical key.
TOKEN_INDEX: dict[str, str] = {}
for _key, _entry in MERCHANT_ALIASES.items():
    TOKEN_INDEX[_key] = _key
    for _token in _entry["tokens"]:
        TOKEN_INDEX[_token.strip().lower()] = _key
