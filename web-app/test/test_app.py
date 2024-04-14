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

def test_home_page_status(client):
    response = client.get('/')
    assert response.status_code == 200

def test_home_page_content(client):
    response = client.get('/')
    assert b"Welcome to the CheckMate" in response.data
    assert b"Upload Receipt" in response.data

def test_numofpeople_page_status(client):
    response = client.get('/numofpeople')
    assert response.status_code == 200

def test_numofpeople_page_form(client):
    response = client.get('/numofpeople')
    assert b"Enter Number of People and Names" in response.data
    assert b"count" in response.data
    assert b"names" in response.data

def test_search_history_page_status(client):
    response = client.get('/search_history')
    assert response.status_code == 200

def test_search_history_content(client):
    response = client.get('/search_history')
    assert b"Receipt History" in response.data
    assert b"Search by Name:" in response.data

def test_upload_receipt_fail_no_file(client):
    response = client.post('/upload', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
        