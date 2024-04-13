import json
import requests

url = "https://ocr.asprise.com/api/v1/receipt"
image = "RestaurantReceipt1.png"

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

with open("response1.json", "w") as f:
    f.write(res.text)

# receiptOcrEndpoint = 'https://ocr.asprise.com/api/v1/receipt' # Receipt OCR API endpoint
# imageFile = "RestaurantReceipt1.png" # // Modify this to use your own file if necessary
# r = requests.post(receiptOcrEndpoint, data = { \
#   'client_id': 'TEST',        # Use 'TEST' for testing purpose \
#   'recognizer': 'auto',       # can be 'US', 'CA', 'JP', 'SG' or 'auto' \
#   'ref_no': 'ocr_python_123', # optional caller provided ref code \
#   }, \
#   files = {"file": open(imageFile, "rb")})

# print(r.text) # result in JSON