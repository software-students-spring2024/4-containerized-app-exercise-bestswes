import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
from flask import jsonify
import sys
from pathlib import Path
from pymongo import MongoClient
import requests  # Corrected import
from bson import ObjectId

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

import main
from main import perform_ocr, pretdict_endpoint

# Setup Flask Test Client
@pytest.fixture
def client():
    main.app.config['TESTING'] = True
    with main.app.test_client() as client:
        yield client

# Mock MongoDB
@pytest.fixture
def mock_mongo(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr(main, 'db', mock_db)
    return mock_db

def test_predict_missing_object_id(client):
    response = client.post('/predict', json={})
    assert response.status_code == 400
    assert 'Object_ID not found in request data' in response.json['error']