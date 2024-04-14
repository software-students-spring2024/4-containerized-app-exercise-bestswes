import os
from flask import Flask, render_template, redirect, request, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client.test

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