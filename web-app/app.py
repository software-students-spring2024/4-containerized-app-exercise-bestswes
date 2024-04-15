import os
from flask import Flask, render_template, redirect, request, url_for, jsonify
import pymongo
from pymongo import MongoClient
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv
from bson import ObjectId
import json

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the templatpip e in env.example
load_dotenv()  # take environment variables from .env.

# instantiate the app
app = Flask(__name__)
app.secret_key = 'a_unique_and_secret_key'
# # turn on debugging if in development mode
if os.getenv("FLASK_ENV", "development") == "development":
#     # turn on d   ebugging, if in development
    app.debug = True  # debug mnode

# connect to the database
cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the database


# Call the ML service to perform OCR on the receipt
def call_ml_service(Object_ID):
    url = "http://machine-learning-client:5002/predict"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({"Object_ID": str(Object_ID)})  # Serialize the Object_ID into a JSON string
    response = requests.post(url, data=data, headers=headers)
    logger.debug(f"Response Status Code: {response.status_code}")
    logger.debug(f"Response Text: {response.text}")
    return response.json()


#homepage -add receipt - history 
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        image_data = file.read()
        try:
            result = db.receipts.insert_one({"image": image_data})
            inserted_id = str(result.inserted_id)
            #logger.debug("YAY", inserted_id)
            call_ml_service(inserted_id)
            return redirect(url_for('numofpeople', receipt_id=inserted_id))
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logger.error("Could not connect to MongoDB: %s", str(e))
            return jsonify({"error": "Database connection failed"}), 503

    return jsonify({"error": "Unexpected error occurred"}), 500


#(  pull receipt from database )
@app.route('/numofpeople/<receipt_id>')
def numofpeople(receipt_id):
    """
    Display the form to enter the number of people and their names.
    """
    return render_template("numofpeople.html", receipt_id=receipt_id)

@app.route('/submit_people/<receipt_id>', methods=["POST"])
def submit_people(receipt_id):
    """
    Process the submitted number of people and names.
    """
    count = request.form['count']
    names = request.form['names']
    # Split the names by comma and strip spaces
    names_list = [name.strip() for name in names.split(',')]

    try:
        # Update the existing document in the receipts collection
        db.receipts.update_one({"_id": ObjectId(receipt_id)}, {"$set": {"num_of_people": count, "names": names_list}})
        return redirect(url_for('select_appetizers', receipt_id=receipt_id))
         # Redirect to another page after submission
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error("Could not connect to MongoDB: %s", str(e))
        return jsonify({"error": "Database connection failed"}), 503
#label appetizers

@app.route('/select_appetizers/<receipt_id>', methods=['GET', 'POST'])
def select_appetizers(receipt_id):
    if request.method == 'POST':
        if 'no_appetizers' in request.form and request.form['no_appetizers'] == 'none':
            logging.debug("No appetizers selected by user.")
            db.receipts.update_one(
                {'_id': ObjectId(receipt_id)},
                {'$set': {'items.$[].is_appetizer': False}}  # Reset all items to not be appetizers
            )
            return redirect(url_for('allocateitems', receipt_id=receipt_id))

        appetizer_ids = request.form.getlist('appetizers')
        logging.debug(f"Received appetizer IDs: {appetizer_ids}")

        valid_ids = [id for id in appetizer_ids if ObjectId.is_valid(id) and id.strip() != '']
        logging.debug(f"Valid appetizer IDs: {valid_ids}")

        if valid_ids:
            object_ids = [ObjectId(id) for id in valid_ids]
            db.receipts.update_many(
                {'_id': ObjectId(receipt_id)},
                {'$set': {'items.$[elem].is_appetizer': True}},
                array_filters=[{'elem._id': {'$in': object_ids}}]
            )
            db.receipts.update_one(
                {'_id': ObjectId(receipt_id)},
                {'$set': {'items.$[elem].is_appetizer': False}},
                array_filters=[{'elem._id': {'$nin': object_ids}}]
            )
        else:
            db.receipts.update_one(
                {'_id': ObjectId(receipt_id)},
                {'$set': {'items.$[].is_appetizer': False}}
            )

        return redirect(url_for('allocateitems', receipt_id=receipt_id))

    receipt = db.receipts.find_one({'_id': ObjectId(receipt_id)})
    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404
    items = receipt.get('items', [])
    return render_template('select_appetizers.html', items=items, receipt_id=receipt_id)


#allocate items -> people 

@app.route('/allocateitems/<receipt_id>', methods=['GET', 'POST'])
def allocateitems(receipt_id):
    if request.method == 'POST':
        # Clear previous allocations to avoid duplicates
        db.receipts.update_one({'_id': ObjectId(receipt_id)}, {'$unset': {'allocations': ''}})

        # Process form data and re-allocate items
        allocations = {key: request.form.getlist(key) for key in request.form.keys()}
        for name, items in allocations.items():
            if items:  # Ensure we don't push empty lists
                db.receipts.update_one(
                    {'_id': ObjectId(receipt_id)},
                    {'$push': {'allocations': {'name': name, 'items': items}}}
                )
        return redirect(url_for('calculate_bill', receipt_id=receipt_id))

    # Fetch data to display form
    receipt = db.receipts.find_one({'_id': ObjectId(receipt_id)})
    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404
    
    people = receipt.get('names', [])
    food_items = receipt.get('items', [])

    return render_template('allocateitems.html', people=people, food_items=food_items, receipt_id=receipt_id)




#calculate total, show total, update receipt in database 

@app.route('/calculate_bill/<receipt_id>')
def calculate_bill(receipt_id):
    try:
        # Convert _id from string to ObjectId and find the receipt
        receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    except:
        return "Invalid ID format", 400

    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404
    
    try:
        num_of_people = int(receipt.get('num_of_people', 0))
    except ValueError:
        return "Invalid number of people", 400

    items = receipt['items']
    diners = receipt['allocations']

    # Assuming tax and tip percentages are stored as part of the receipt
    tax_rate = receipt.get('tax_rate', 8.75) / 100
    tip_percentage = receipt.get('tip_percentage', 18) / 100

    # Calculate total cost of appetizers and split equally
    appetizer_total = sum(item['amount'] for item in items if item.get('is_appetizer') is True)
    logger.debug("Appetizer total: $%.2f", appetizer_total)  # Properly formatted log message

    if num_of_people > 0:
        appetizer_split = appetizer_total / num_of_people
    else:
        appetizer_split = 0

    logger.debug("Appetizer split per person: $%.2f", appetizer_split)
    # Initialize a dictionary to hold each diner's total, starting with the appetizer split
    payments = {}
    logger.debug("payments", payments)
    subtotal = sum(item['amount'] for item in items)
    logger.debug("subt", subtotal)

    # Calculate total tax and tip
    total_tax = subtotal * tax_rate
    logger.debug(total_tax)
    total_tip = subtotal * tip_percentage
    logger.debug(total_tip)

    # Adjust appetizer split to include proportional tax and tip
    appetizer_split += (appetizer_split / subtotal) * (total_tax + total_tip) if subtotal > 0 else 0

    # Process each diner's payment
    for diner in diners:
        diner_name = diner['name']
        diner_items = diner['items']
        total = appetizer_split  # Start with their share of appetizers including tax and tip
        diner_dishes_total = sum(item['amount'] for item in items if item['description'] in diner_items)

        # Add diner's share of tax and tip based on their ordered items
        diner_tax = diner_dishes_total * tax_rate
        diner_tip = diner_dishes_total * tip_percentage
        total += diner_dishes_total + diner_tax + diner_tip

        payments[diner_name] = total
        logger.debug("updated payments", payments)

    # Update the receipt with the calculated payments
    db.receipts.update_one({"_id": ObjectId(receipt_id)}, {'$set': {'payments': payments}})

    return jsonify(payments), 200


@app.route("/search_history")
def search_history():
    return render_template("search_history.html")

#route to show all the receipts history with functionality to search a keyword
@app.route("/history")
def history():
    keyword = request.args.get('search', None)
    
    query = {}
    if keyword:
        query = {"name": {"$regex": keyword, "$options": "i"}}
    
    items = db.receipts.find(query)
    items_list = list(items)

    return render_template("search_history.html", items=items_list)

@app.route('/test_mongodb')
def test_mongodb():
    try:
        info = db.command('serverStatus')
        return jsonify(success=True, message="Successfully connected to MongoDB", info=info), 200
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500
@app.route('/test_ml_service')
def test_ml_service():
    response = requests.get('http://machine-learning-client:5002/test_connection')
    if response.status_code == 200:
        return jsonify(success=True, message="Connected to ML service", response=response.json()), 200
    else:
        return jsonify(success=False, message="Failed to connect to ML service"), 500
@app.route('/test_connection', methods=['GET'])
def test_connection():
    return jsonify(success=True, message="Machine Learning Client is reachable"), 200

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 10000))  # Default to 5000 if FLASK_PORT is not set

    app.run(debug=True, host='0.0.0.0')
