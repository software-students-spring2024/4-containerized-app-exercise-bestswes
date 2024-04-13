from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://mongodb:27017/')  # This is the default Docker link
db = client['test_db']  # 'test_db' is the name of the database

@app.route('/')
def home():
    return "MongoDB is connected!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
