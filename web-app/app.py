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
#ask for num people / names 
#label appetizers
#allocate items -> people 
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