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
    receipt_id = request.form['receipt_id']  # This should be passed as part of the form submission
    count = request.form['count']
    names = request.form['names']
    names_list = [name.strip() for name in names.split(',')]
    
    # Update the receipt document in the 'receipts' collection
    result = db.receipts.update_one(
        {"_id": ObjectId(receipt_id)},
        {"$set": {"num_of_people": int(count), "people_names": names_list}}
    )
    
    if result.matched_count == 0:
        return "Receipt not found", 404  # If no document matches the ID, return an error
    if result.modified_count == 0:
        return "No update performed", 404  # If no document was modified, return an error

    return redirect(url_for('home'))  # Redirect to home after submission

#label appetizers
@app.route('/select_appetizers/<receipt_id>', methods=['GET', 'POST'])
def select_appetizers(receipt_id):
    if request.method == 'POST':
        appetizer_ids = [ObjectId(id) for id in request.form.getlist('appetizers')]
        # Update the specific receipt document to mark items as appetizers
        db.receipts.update_one(
            {"_id": ObjectId(receipt_id)},
            {"$set": {"items.$[elem].is_appetizer": True}},
            array_filters=[{"elem._id": {"$in": appetizer_ids}}]
        )
        
        return redirect(url_for('select_appetizers', receipt_id=receipt_id))

    # Fetch the specific receipt and its food items
    receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    items = receipt['items'] if receipt else []
    return render_template('select_appetizers.html', items=items, receipt_id=receipt_id)



#allocate items -> people 

@app.route('/allocateitems/<receipt_id>', methods=['GET', 'POST'])
def allocateitems(receipt_id):
    if request.method == 'POST':
        # Retrieve form data, structured as {name: [list of food item ids]}
        allocations = {key: request.form.getlist(key) for key in request.form.keys() if key != 'receipt_id'}
        
        # Update the specific receipt with new allocations
        for name, items in allocations.items():
            db.receipts.update_one(
                {"_id": ObjectId(receipt_id)},
                {"$set": {"allocations": {name: items}}}
            )

        return redirect(url_for('allocateitems', receipt_id=receipt_id))

    receipt = db.receipts.find_one({"_id": ObjectId(receipt_id)})
    people = receipt['people_names'] if receipt else []
    food_items = [item for item in receipt['items'] if not item.get('is_appetizer', False)] if receipt else []
    return render_template('allocateitems.html', people=people, food_items=food_items, receipt_id=receipt_id)


#calculate total, show total, update receipt in database 

@app.route('/calculate_bill/<receipt_id>')
def calculate_bill(receipt_id):
    receipt = db.receipts.find_one({"_id": receipt_id})
    if not receipt:
        return "Receipt not found", 404

    num_of_people = receipt['num_of_people']
    items = receipt['items']

    # Calculate total cost of appetizers and split equally
    appetizer_total = sum(item['price'] for item in items if item['is_appetizer'])
    appetizer_split = appetizer_total / num_of_people if num_of_people else 0

    # Initialize a dictionary to hold each diner's total, starting with the appetizer split
    payments = {}
    for person, dishes in db.diners.items():
        total = 0
        for dish in dishes:
            if dish in db.receipts.items:
                total += db.receipts.items[dish]
        total += appetizer_split
        payments[person] = total
    return payments

    db.receipts.find_one_and_update({"_id": receipt_id}, payments)



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