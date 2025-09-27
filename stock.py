import requests
from bs4 import BeautifulSoup
import time
import json
import os
import sys

# ==============================
# Config from command line args
# ==============================
# Usage:
#   python stock.py AAPL NASDAQ
#   python stock.py RELIANCE NSE
#
ticker = sys.argv[1] if len(sys.argv) > 1 else "Reliance"
exchange = sys.argv[2] if len(sys.argv) > 2 else "NSE"

# folder where JSONs should be stored (relative to this script)
JSON_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Company-Jsons"))
os.makedirs(JSON_FOLDER, exist_ok=True)

# full path for this ticker's JSON file
array_file = os.path.join(JSON_FOLDER, f"{ticker}.json")



base_url = f"https://www.google.com/finance/quote/{ticker}:{exchange}?hl=en"
class_name = "YMlKec fxKbKc"

# ==============================
# Fetch current price
# ==============================
def fetch_price():
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find(class_=class_name)

        if price_element:
            price = price_element.text.strip()[1:].replace(",", "")
            print(f"💹 Current price of {ticker} ({exchange}): {price}")
            return float(price)
        else:
            print("⚠️ Price element not found. The page structure may have changed.")
            return None
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return None

# ==============================
# Append entry to JSON file
# ==============================
def append_to_array(entry):
    if os.path.exists(array_file):
        try:
            with open(array_file, "r") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    data.append(entry)

    try:
        with open(array_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Error writing to file: {e}")

# ==============================
# Main loop
# ==============================
try:
    while True:
        price = fetch_price()
        if price:
            entry = {
                "ticker": ticker,
                "exchange": exchange,
                "price": price,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            append_to_array(entry)

        time.sleep(10)  # poll every 3 seconds
except KeyboardInterrupt:
    print("🛑 Stopped by user.")
