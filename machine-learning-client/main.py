import json
import requests

# Use receipt-OCR.py to get response1.json
# (can only do this a couple times an hour with the test API key)

# Load response1.json
with open("response1.json", "r") as f:
    data = json.load(f)

print('Receipt Keys:', data['receipts'][0].keys())
items = data['receipts'][0]['items']
print()
print(f"Your purchase at {data['receipts'][0]['merchant_name']}")

for item in items:
    print(f"{item['description']} - {data['receipts'][0]['currency']} {item['amount']}")
print("-" * 20)
print(f"Subtotal: {data['receipts'][0]['currency']} {data['receipts'][0]['subtotal']}")
print(f"Tax: {data['receipts'][0]['currency']} {data['receipts'][0]['tax']}")
print("-" * 20)
print(f"Total: {data['receipts'][0]['currency']} {data['receipts'][0]['total']}")
# print(data['receipts'])