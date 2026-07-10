import csv
import requests
import json
import time

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

WEBHOOK = "***REMOVED***"

## Procedures

def read():
    data = []
    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)

        for row in reader:
            data.append(row)

    return data


def evaluate(card, target, name):
    url = apiurl.replace("pid", str(card))
    response = getJson(url).json()
    listings = response["results"][0]["results"]

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
            message = name + " at $" + str(total) + ": " + link.replace("pid", str(card))
            requests.post(
                WEBHOOK,
                json={
                    "content": message
                }
            )
        elif (price + shipping/2 < target):
            print("Almost worthy listing")



def getJson(url):
    response = requests.post(
        url,
        headers=headers,
        json=payload
    )
    return response

## The program

data = read()

for card, price, name in data:
    print(f"Card: "+ name + f"")
    evaluate(card, float(price), name)
    time.sleep(10)7EC7-5966

