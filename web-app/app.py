import os
from flask import Flask, render_template, redirect, request, url_for, jsonify
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
    # Check if the post request has the file part
    if 'receipt_image' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['receipt_image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process other form data
        image_data = request.form.get("image_data")
        if not image_data:
            return jsonify({"error": "Missing image data"}), 400
        
        try:
            # Insert document into MongoDB
            result = db.images.insert_one({"image_data": image_data})
            object_id = result.inserted_id
            print('ObjectID: ', object_id)
            
            # Call ML service or perform other processing
            call_ml_service(str(object_id))
            return redirect(url_for('home'))
        except pymongo.errors.PyMongoError as e:
            logging.error("Failed to insert document into MongoDB", exc_info=True)
            return jsonify({"error": "Database insertion failed"}), 500
    
    return jsonify({"error": "File upload failed"}), 400




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
    diners = receipt.get('allocations', [])  # Get diners field

    # Extract tax and tip percentages from the receipt
    tax_rate = 0.0875  # Default tax rate of 8.75%
    tip_percentage = receipt.get('tip_percentage', 0) / 100  # Convert tip percentage to decimal

    # Calculate total cost of appetizers and split equally
    appetizer_total = sum(item['price'] for item in items if item.get('is_appetizer', False))
    appetizer_split = appetizer_total / num_of_people if num_of_people > 0 else 0

    # Initialize a dictionary to hold each diner's total, starting with the appetizer split
    payments = {}

    # Calculate the total cost before tax and tip to determine the base for these calculations
    subtotal = sum(item['price'] for item in items)

    # Calculate total tax and tip
    total_tax = subtotal * tax_rate
    total_tip = subtotal * tip_percentage

    # Adjust appetizer split to include proportional tax and tip
    appetizer_split += (appetizer_split / subtotal) * (total_tax + total_tip)

    # Process each diner's payment
    for diner in diners:
        diner_name = diner['name']
        total = appetizer_split  # Start with their share of appetizers including tax and tip
        diner_dishes_total = sum(item['price'] for item in items if item['name'] in diner['dishes'])

        # Add diner's share of tax and tip based on their ordered items
        diner_tax = diner_dishes_total * tax_rate
        diner_tip = diner_dishes_total * tip_percentage
        total += diner_dishes_total + diner_tax + diner_tip

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
    app.run(debug=True, host='0.0.0.0')
