import pytest
from app.main import app as flask_app
import logging
from unittest.mock import MagicMock, patch
import os
import base64
import websocket
import socket
import subprocess

@pytest.fixture(autouse=True)
def mock_logging(monkeypatch):
    """Mock the logging file handler to avoid permission errors."""
    mock_file_handler = MagicMock()
    monkeypatch.setattr(logging, 'FileHandler', lambda filename: mock_file_handler)

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    os.environ['DIAG_USERNAME'] = 'testuser'
    os.environ['DIAG_PASSWORD'] = 'testpass'
    yield flask_app
    del os.environ['DIAG_USERNAME']
    del os.environ['DIAG_PASSWORD']

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def auth_headers():
    """Authentication headers for diag endpoints."""
    return {
        'Authorization': 'Basic ' + base64.b64encode(b"testuser:testpass").decode('utf-8')
    }

def test_index(client):
    """Test the index page."""
    response = client.get('/api/')
    assert response.status_code == 200

def test_echo_websocket(live_server, auth_headers):
    """Test the websocket echo endpoint."""
    url = f"ws://localhost:{live_server.port}/api/ws/echo"
    ws = websocket.create_connection(url, header=auth_headers)
    try:
        message = "Hello, WebSocket!"
        ws.send(message)
        response = ws.recv()
        assert response == message
    finally:
        ws.close()

def test_ping(client, auth_headers, monkeypatch):
    """Test the ping endpoint."""
    mock_check_output = MagicMock(return_value="PING google.com (142.250.180.14) 56(84) bytes of data.")
    monkeypatch.setattr(subprocess, 'check_output', mock_check_output)
    response = client.get('/api/ping?host=google.com', headers=auth_headers)
    assert response.status_code == 200
    assert b"PING google.com" in response.data

def test_dns_resolve(client, auth_headers, monkeypatch):
    """Test the dns resolve endpoint."""
    mock_getaddrinfo = MagicMock(return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('1.2.3.4', 0))])
    monkeypatch.setattr(socket, 'getaddrinfo', mock_getaddrinfo)
    response = client.get('/api/dns?name=google.com', headers=auth_headers)
    assert response.status_code == 200
    assert response.json == {"addresses": ["1.2.3.4"]}

def test_curl(client, auth_headers, monkeypatch):
    """Test the curl endpoint."""
    mock_response = MagicMock()
    mock_response.text = "Hello from curl"
    mock_response.status_code = 200
    mock_response.headers = {'Content-Type': 'text/plain'}
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr('requests.get', mock_get)
    response = client.get('/api/curl?url=http://example.com', headers=auth_headers)
    assert response.status_code == 200
    assert b"Hello from curl" in response.data

def test_tcp_check(client, auth_headers, monkeypatch):
    """Test the tcp check endpoint."""
    mock_create_connection = MagicMock()
    monkeypatch.setattr(socket, 'create_connection', mock_create_connection)
    response = client.get('/api/tcp-check?host=google.com&port=80', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['status'] == 'success'

def test_echo_headers(client, auth_headers):
    """Test the echo headers endpoint."""
    response = client.get('/api/headers', headers=auth_headers)
    assert response.status_code == 200
    assert 'Authorization' in response.json

def test_echo_body(client, auth_headers):
    """Test the echo body endpoint."""
    response = client.post('/api/echo', headers=auth_headers, data="Hello, body!")
    assert response.status_code == 200
    assert b"Hello, body!" in response.data

def test_random_error(client, auth_headers):
    """Test the random error endpoint."""
    response = client.get('/api/random-error', headers=auth_headers)
    assert response.status_code in [400, 401, 403, 404, 500, 502, 503, 504]
