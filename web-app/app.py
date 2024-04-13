import os
from flask import Flask, render_template, redirect, request, url_for
from pymongo import MongoClient

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client.test

#homepage -add receipt - history 

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