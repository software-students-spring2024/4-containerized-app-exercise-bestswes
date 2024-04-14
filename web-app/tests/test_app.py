# tests/test_app.py
import pytest
from app import app as flask_app  # Import your Flask app

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Expected Content in Home Page" in response.data
