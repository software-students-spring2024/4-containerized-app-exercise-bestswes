from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
import json
from bson import ObjectId

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


app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def pretdict_endpoint():
    # Get the image data from the request
    Object_ID = ObjectId(request.data)
    image = db.receipts.find_one({"_id": Object_ID})['image_data']

    # Here, you would add the code to perform OCR on the image
    # For now, let's assume you have a function called perform_ocr that does this
    
    # data = perform_ocr(image)
    data = json.load(open("response1.json", "r"))

    # Create a MongoDB client
    client = MongoClient('mongodb://db:27017/')

    # Connect to your database (replace 'mydatabase' with your database name)
    db = client['db']

    # Connect to your collection (replace 'mycollection' with your collection name)
    collection = db['receipts']

    # Prepare the data to be inserted into the database
    receipt = data['receipts'][0]
    receipt_data = {
        'receipt_name': receipt['merchant_name'],
        'currency': receipt['currency'],
        'items': [{'description': item['description'], 'amount': item['amount']} for item in receipt['items']],
        'total': receipt['total'],
        'tax': receipt['tax'],
        'tip': receipt['tip'],
        'subtotal': receipt['subtotal'],
    }

    # Update the document with given ObjectId
    collection.update_one({'_id': Object_ID}, {'$set': receipt_data})
    inserted_id = Object_ID

    # Return the inserted_id as a JSON response
    return jsonify({'_id': str(inserted_id)})

def perform_ocr(image):
    url = "https://ocr.asprise.com/api/v1/receipt"

    # Get response (can only do this a couple times with the test API key)
    res = requests.post(url, 
                        data = {
                            'api_key': 'TEST',
                            'recognizer': 'auto',
                            'ref_no': 'ocr_python_123'
                        },
                        files = {
                            'file': open(image, "rb")
                        })

    with open("response.json", "w") as f:
        f.write(res.text)
    
    return res.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)  # Run the app