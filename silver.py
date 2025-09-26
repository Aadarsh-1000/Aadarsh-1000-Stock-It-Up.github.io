import requests
from bs4 import BeautifulSoup
import time
import json
import os

ticker = "TCS"
exchange = "NSE"
base_url = f"https://www.google.com/finance/quote/{ticker}:{exchange}?hl=en"
class_name = "YMlKec fxKbKc"

array_file = "array.json"


def fetch_price():
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find(class_=class_name)

        if price_element:
            price = price_element.text.strip()[1:].replace(",", "")
            print(f"💹 Current price of {ticker}: {price}")
            return float(price)
        else:
            print("⚠️ Price element not found. The page structure may have changed.")
            return None
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return None

def append_to_array(entry):
    if os.path.exists(array_file):
        try:
            with open(array_file, "r") as f:
                print(f"📁 Logging to: {os.path.abspath(array_file)}")
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

        time.sleep(3)
except KeyboardInterrupt:
    print("🛑 Stopped by user.")
