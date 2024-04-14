import os
from flask import Flask, render_template, redirect, request, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId


app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client.test

#homepage -add receipt - history 
@app.route('/')
def home():
    return render_template('home.html')
#get image route -create new receipt in databse  
@app.route("/upload_image", methods=["POST"])
def upload_image():
    """
    Send the initial unprocessed image to MongoDB.
    """
    image_data = request.form["image_data"]
    if image_data != "test":
        db.receipts.insert_one({"image_data": image_data})
    #return redirect(url_for("display"))

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