import os
from flask import Flask, render_template, redirect, request, url_for
from pymongo import MongoClient
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


@app.route('/history')
def history():
    # Implement retrieval and display of receipt history
    return render_template('history.html')

#(  pull receipt from database )
#ask for num people / names 
#label appetizers
#allocate items -> people 

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