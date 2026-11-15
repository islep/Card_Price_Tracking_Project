import csv
import requests
import json
import time
import os
import sys
from dotenv import load_dotenv

# Locally, read DISCORD_WEBHOOK from the .env file (never committed).
# On GitHub Actions there is no .env, so the repository secret is used instead.
load_dotenv()

## Global Variables
filename = "Cards.csv"
apiurl = "https://mp-search-api.tcgplayer.com/v1/product/pid/listings"
link = "https://www.tcgplayer.com/product/pid?Language=English"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.tcgplayer.com",
    "Referer": "https://www.tcgplayer.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

payload = {
    "filters": {
        "term": {
            "sellerStatus": "Live",
            "channelId": 0,
            "language": ["English"]
        },
        "range": {
            "quantity": {
                "gte": 1
            }
        },
        "exclude": {
            "channelExclusion": 0
        }
    },
    "from": 0,
    "size": 10,
    "sort": {
        "field": "price+shipping",
        "order": "asc"
    },
    "context": {
        "shippingCountry": "US",
        "cart": {}
    }
}

WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

if not WEBHOOK:
    sys.exit("ERROR: DISCORD_WEBHOOK is missing. Add it to your .env file when running locally, or as a GitHub secret when running on GitHub Actions.")

failures = []

## Procedures

def read():
    data = []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            reader = csv.reader(file)

            for line, row in enumerate(reader, start=1):
                if not row:
                    continue
                if len(row) != 3:
                    print(f"ERROR: {filename} line {line} should have 3 values (card id, target price, name) but has {len(row)}: {row}")
                    failures.append(f"{filename} line {line}")
                    continue
                card, price, name = row
                try:
                    data.append((card, float(price), name))
                except ValueError:
                    print(f"ERROR: {filename} line {line} has an invalid target price '{price}' for {name}")
                    failures.append(f"{filename} line {line}")
    except FileNotFoundError:
        sys.exit(f"ERROR: Could not find {filename}. Make sure you are running the program from the project folder.")

    return data


def evaluate(card, target, name):
    url = apiurl.replace("pid", str(card))
    try:
        listings = getJson(url)["results"][0]["results"]
    except requests.exceptions.Timeout:
        return "TCGplayer took too long to respond"
    except requests.exceptions.HTTPError as error:
        return f"TCGplayer returned HTTP status {error.response.status_code}"
    except requests.exceptions.JSONDecodeError:
        return "TCGplayer did not send back valid data"
    except requests.exceptions.ConnectionError:
        return "Could not connect to TCGplayer. Check your internet connection"
    except requests.exceptions.RequestException as error:
        return f"Request to TCGplayer failed: {error}"
    except (KeyError, IndexError, TypeError):
        return "TCGplayer's response was not in the expected format. The card id may be wrong or the site may have changed"

    lowest = None

    for listing in listings:
        seller = listing.get("sellerName", "Unknown")
        condition = listing.get("condition", "Unknown")
        price = listing.get("price", 0)
        shipping = listing.get("sellerShippingPrice", 0)
        total = price + shipping

        if (total < target):
            print(f"Found worthy listing!!\n"
                f"{seller:30} | "
                f"{condition:15} | "
                f"Base Price: ${price:6.2f} | "
                f"Shipping: ${shipping:4.2f} | "
                f"Total: ${total:6.2f}"
            )
            if lowest is None or total < lowest:
                lowest = total
        elif (price + shipping/2 < target):
            print("Almost worthy listing")

    if lowest is not None:
        message = name + " at $" + str(round(lowest, 2)) + ": " + link.replace("pid", str(card))
        try:
            response = requests.post(
                WEBHOOK,
                json={
                    "content": message
                },
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            return f"Discord rejected the alert with HTTP status {error.response.status_code}. Check that DISCORD_WEBHOOK is correct"
        except requests.exceptions.RequestException:
            return "Could not send the alert to Discord"

    return None


def getJson(url):
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()

## The program

data = read()

for card, price, name in data:
    print(f"Card: "+ name + f"")
    error = evaluate(card, price, name)
    if error:
        print(f"ERROR for {name} (card id {card}): {error}")
        failures.append(name)
    time.sleep(5)

if failures:
    sys.exit(f"Finished with errors for {len(failures)} item(s): {', '.join(failures)}")

