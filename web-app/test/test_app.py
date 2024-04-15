import pytest
from flask import url_for
import os
import tempfile
import io
from unittest.mock import patch
import sys
from pathlib import Path
import mongomock
import requests_mock
from bson import ObjectId

# Adjust the Python path to include the directory above the 'test' directory where 'app.py' is located
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent  # 'web_app' directory
sys.path.insert(0, str(parent_dir))

from app import app  # Now you can successfully import app
from app import call_ml_service  # Assuming call_ml_service is in app.py

# Use a valid ObjectId for tests
test_id = str(ObjectId())


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def mock_db(monkeypatch):
    mock_client = mongomock.MongoClient()
    monkeypatch.setattr('pymongo.MongoClient', lambda *args, **kwargs: mock_client)
    db = mock_client['test_db']  # simulate the database
    # Now simulate collections within this database
    db.create_collection("receipts")
    db.create_collection("images")
    return db

@pytest.fixture
def mock_requests(monkeypatch):
    """
    Create a fixture that mocks requests.post method to prevent actual HTTP calls in tests.
    """
    with requests_mock.Mocker() as m:
        monkeypatch.setattr("requests.post", m.post)
        yield m

@pytest.fixture
def prepare_data(mock_db):
    """Prepare the database with dummy data."""
    receipt_id = ObjectId()
    mock_db.receipts.insert_one({
        "_id": receipt_id,
        "names": ["Alice", "Bob"],
        "items": [
            {"_id": ObjectId(), "description": "Salad", "price": 10.00, "is_appetizer": True},
            {"_id": ObjectId(), "description": "Steak", "price": 25.00, "is_appetizer": False}
        ],
        "allocations": [
            {"name": "Alice", "items": ["Salad"]},
            {"name": "Bob", "items": ["Steak"]}
        ],
        "num_of_people": 2
    })
    return receipt_id

def test_home_page_status(client):
    response = client.get('/')
    assert response.status_code == 200

def test_home_page_content(client):
    response = client.get('/')
    assert b"Welcome to CheckMate" in response.data
    assert b"Upload Receipt" in response.data

def test_home_link_to_upload(client):
    """Check if the home page has a link to the upload page."""
    response = client.get('/')
    assert b'action="/upload"' in response.data
    assert b'method="post"' in response.data
    assert b'enctype="multipart/form-data"' in response.data
    
def test_home_page(client):
    """Test loading the home page."""
    response = client.get('/')
    assert response.status_code == 200
    assert 'Welcome to CheckMate' in response.get_data(as_text=True)

def test_search_history_page_status(client):
    response = client.get('/search_history')
    assert response.status_code == 200

def test_search_history_content(client):
    response = client.get('/search_history')
    assert b"Receipt History" in response.data
    assert b"Search by Name:" in response.data

def test_empty_history_search(client, mock_db):
    response = client.get('/history?search=nonexistent')
    assert response.status_code == 200
    assert 'No results found.' in response.get_data(as_text=True)
    
def test_upload_image_failure(client):
    """Test the image upload failure due to missing file."""
    response = client.post('/upload', data={})
    assert response.status_code == 400
    assert 'No image part' in response.get_data(as_text=True)

def test_numofpeople_page_status(client):
    # Correcting the test to include the required `receipt_id`
    response = client.get(f'/numofpeople/{test_id}')
    assert response.status_code == 200
    
def test_calculate_bill_invalid_id(client):
    response = client.get('/calculate_bill/invalid_id')
    assert response.status_code == 400
    assert "Invalid ID format" in response.get_data(as_text=True)

def test_numofpeople_page(client, mock_db):
    test_id = str(ObjectId())
    mock_db.receipts.insert_one({"_id": ObjectId(test_id), "num_of_people": None, "names": []})
    response = client.get(f'/numofpeople/{test_id}')
    assert response.status_code == 200
    assert "Number of People" in response.get_data(as_text=True)

def test_submit_people(client, mock_db):
    test_id = str(ObjectId())
    mock_db.receipts.insert_one({"_id": ObjectId(test_id)})
    data = {'count': '4', 'names': 'John, Jane, Doe, Ann'}
    response = client.post(f'/submit_people/{test_id}', data=data)
    assert response.status_code == 302

# Testing select_appetizers page
def test_select_appetizers_no_ids(client, mock_db):
    test_id = str(ObjectId())
    mock_db.receipts.insert_one({"_id": ObjectId(test_id), "items": [{"_id": ObjectId(), "description": "Fries", "is_appetizer": False}]})
    response = client.post(f'/select_appetizers/{test_id}', data={})
    assert response.status_code == 302
    assert '/select_appetizers' in response.headers['Location']

def test_select_appetizers_valid_ids(client, mock_db):
    test_id = str(ObjectId())
    item_id = ObjectId()
    mock_db.receipts.insert_one({"_id": ObjectId(test_id), "items": [{"_id": item_id, "description": "Burger"}]})
    response = client.post(f'/select_appetizers/{test_id}', data={'appetizers': str(item_id)})
    assert response.status_code == 302
    assert '/allocateitems' in response.headers['Location']

def test_allocateitems_post_success(client, mock_db):
    test_id = str(ObjectId())
    item_id = ObjectId()
    mock_db.receipts.insert_one({"_id": ObjectId(test_id), "names": ["Alice", "Bob"], "items": [{"_id": item_id, "description": "Pizza"}]})
    response = client.post(f'/allocateitems/{test_id}', data={'Alice': str(item_id)})
    assert response.status_code == 302
    assert '/calculate_bill' in response.headers['Location']

def test_select_appetizers(client, prepare_data):
    """Test the POST request to select appetizers."""
    response = client.post(f'/select_appetizers/{prepare_data}', data={'appetizers': str(ObjectId())})
    assert response.status_code == 302
    assert '/allocateitems' in response.headers['Location']

def test_allocateitems(client, prepare_data):
    """Test the POST request to allocate items to people."""
    response = client.post(f'/allocateitems/{prepare_data}', data={'Alice': str(ObjectId()), 'Bob': str(ObjectId())})
    assert response.status_code == 302
    assert '/calculate_bill' in response.headers['Location']

def test_numofpeople_form_render(client, prepare_data):
    response = client.get(f'/numofpeople/{prepare_data}')
    assert response.status_code == 200
    assert "Enter Number of People and Names" in response.get_data(as_text=True)
    assert "Number of People:" in response.get_data(as_text=True)
    assert "Names (comma separated):" in response.get_data(as_text=True)

def test_allocation_submission(client, mock_db, prepare_data):
    data = {'Alice': 'Salad', 'Bob': 'Steak'}
    response = client.post(f'/allocateitems/{prepare_data}', data=data)
    assert response.status_code == 302
    assert '/calculate_bill' in response.headers['Location']
    updated_doc = mock_db.receipts.find_one({"_id": prepare_data})
    assert 'allocations' in updated_doc

def test_receipt_not_found(client):
    """Ensure the correct error message when a receipt is not found."""
    response = client.get(f'/calculate_bill/{str(ObjectId())}')
    assert response.status_code == 404
    assert "Receipt not found" in response.get_data(as_text=True)

def test_update_appetizers(client, prepare_data, mock_db):
    """Test the update functionality of selecting appetizers."""
    item_id = ObjectId()
    mock_db.receipts.update_one({'_id': prepare_data}, {'$push': {'items': {'_id': item_id, 'description': 'Wings', 'price': 12.00}}})
    response = client.post(f'/select_appetizers/{prepare_data}', data={'appetizers': str(item_id)})
    assert response.status_code == 302
    updated_doc = mock_db.receipts.find_one({'_id': prepare_data})
    assert updated_doc['items'][0]['is_appetizer']  # Validate that the item is now marked as an appetizer

@pytest.mark.timeout(5)
def test_response_time_for_large_operations(client, mock_db):
    large_data = [{"_id": ObjectId(), "name": f"Item {i}", "price": i} for i in range(1000)]
    mock_db.receipts.insert_many(large_data)
    response = client.get('/history')
    assert response.status_code == 200, "Should handle large operations within acceptable time"

def test_no_data_leakage(client, prepare_data):
    response = client.get(f'/numofpeople/{prepare_data}')
    sensitive_data_snippets = ["ssn", "password", "secret"]
    assert not any(snippet in response.get_data(as_text=True).lower() for snippet in sensitive_data_snippets), "No sensitive data should be displayed to the user"

def test_undefined_route(client):
    response = client.get('/undefined_route')
    assert response.status_code == 404
