import pytest
from unittest.mock import patch, mock_open
import json
from flask import jsonify
import sys
from pathlib import Path
from pymongo import MongoClient

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

import main
from main import perform_ocr, pretdict_endpoint

@pytest.fixture
def client():
    main.app.config['TESTING'] = True
    with main.app.test_client() as client:
        yield client

@pytest.fixture
def mock_response():
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json.dumps(json_data)

        def json(self):
            return self.json_data

    return MockResponse({"receipts": [{"currency": "USD", "total": "100"}]}, 200)

def test_perform_ocr(mock_response):
    # Mocking the requests.post to return our mock_response and open to handle both read and write
    with patch('requests.post', return_value=mock_response) as mock_post:
        with patch('builtins.open', mock_open(read_data="data")) as mock_file:
            result = main.perform_ocr("dummy.jpg")
            mock_post.assert_called_once()
            assert mock_file.call_count == 2  # Check for two calls to open: one read, one write
            assert result['receipts'][0]['currency'] == 'USD'
            assert result['receipts'][0]['total'] == '100'


