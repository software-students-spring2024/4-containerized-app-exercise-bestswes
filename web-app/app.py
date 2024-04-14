import os
from flask import Flask, render_template, redirect, request, url_for
from pymongo import MongoClient
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client.test

# Call the ML service to perform OCR on the receipt
def call_ml_service(Object_ID):
    url = "http://machine-learning-client:5002/predict"
    response = requests.post(url, data=Object_ID)
    return response.json()

#homepage -add receipt - history 
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['POST'])
def upload_receipt():
    file = request.files['receipt_image']
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Implement any processing or database storage as necessary
        image_data = request.form["image_data"]
        Object_ID = 0
        if image_data != "test":
            result = db.images.insert_one({"image_data": image_data})
            Object_ID = result.inserted_id
        print('ObjectID: ', Object_ID)
        call_ml_service(Object_ID)
        return redirect(url_for('home'))
    return 'File upload failed', 400




#(  pull receipt from database )
@app.route('/numofpeople')
def numofpeople():
    """
    Display the form to enter the number of people and their names.
    """
    return render_template("numofpeople.html")

@app.route('/submit_people', methods=["POST"])
def submit_people():
    """
    Process the submitted number of people and names.
    """
    count = request.form['count']
    names = request.form['names']
    # Split the names by comma and strip spaces
    names_list = [name.strip() for name in names.split(',')]
    
    # Example: Store in the database or perform other operations
    db.people.insert_one({"count": count, "names": names_list})
    
    return redirect(url_for('search_history'))  # Redirect to another page after submission

#label appetizers
@app.route('/select_appetizers', methods=['GET', 'POST'])
def select_appetizers():
    if request.method == 'POST':
        # Retrieve a list of IDs for the items marked as appetizers
        appetizer_ids = request.form.getlist('appetizers')
        
        # Update the database: set 'is_appetizer' to True for checked items and False otherwise
        db.food_items.update_many({}, {'$set': {'is_appetizer': False}})
        db.food_items.update_many({'_id': {'$in': [ObjectId(id) for id in appetizer_ids]}}, {'$set': {'is_appetizer': True}})
        
        return redirect(url_for('select_appetizers'))

    # Fetch all food items from the database
    items = db.food_items.find()
    return render_template('select_appetizers.html', items=items)



#allocate items -> people 

@app.route('/allocateitems', methods=['GET', 'POST'])
def allocateitems():
    if request.method == 'POST':
        # Retrieve form data, structured as {name: [list of food item ids]}
        allocations = {key: request.form.getlist(key) for key in request.form.keys()}
        
        # Clear previous allocations
        db.allocations.drop()
        
        # Insert new allocations ensuring no item is assigned more than once
        used_items = set()
        for name, items in allocations.items():
            new_items = [item for item in items if item not in used_items]
            used_items.update(new_items)
            if new_items:
                db.allocations.insert_one({"name": name, "items": new_items})
        
        return redirect(url_for('allocateitems'))

    people = db.people.find()
    food_items = db.food_items.find({'is_appetizer': False})

    return render_template('allocateitems.html', people=people, food_items=food_items)


#calculate total, show total, update receipt in database 

from bson import ObjectId
from flask import Flask, jsonify, abort
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client['yourdatabase']

@app.route('/calculate_bill/<_id>')
def calculate_bill(_id):
    try:
        # Convert _id from string to ObjectId and find the receipt
        receipt = db.receipts.find_one({"_id": ObjectId(_id)})
    except:
        return "Invalid ID format", 400

    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404

    num_of_people = receipt['num_of_people']
    items = receipt['items']
    diners = receipt.get('allocations', [])  # Get diners field, defaulting to an empty list if not found

    # Calculate total cost of appetizers and split equally
    appetizer_total = sum(item['price'] for item in items if item.get('is_appetizer', False))
    appetizer_split = appetizer_total / num_of_people if num_of_people > 0 else 0

    # Initialize a dictionary to hold each diner's total, starting with the appetizer split
    payments = {}

    # Process each diner's payment, assuming each diner object includes a name and a list of dish names
    for diner in diners:
        diner_name = diner['name']
        total = appetizer_split
        for dish_name in diner['dishes']:
            # Find dish price from items list
            for item in items:
                if item['name'] == dish_name:
                    total += item['price']
                    break
        payments[diner_name] = total

    # Update the receipt with the calculated payments
    db.receipts.update_one({"_id": ObjectId(_id)}, {'$set': {'payments': payments}})

    return jsonify(payments), 200


if __name__ == '__main__':
    app.run(debug=True)



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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')