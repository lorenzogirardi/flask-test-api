from flask import Blueprint, jsonify, request, Response
from .auth import requires_auth
from .utils import sock
from simple_websocket.errors import ConnectionClosed
import subprocess
import socket
import requests
import random

diag_bp = Blueprint('diag', __name__)

@diag_bp.route('/api/ping', methods=['GET'])
@requires_auth
def ping():
    """
    Runs a ping command to the specified host.
    ---
    parameters:
      - name: host
        in: query
        type: string
        required: true
        description: The host to ping.
      - name: count
        in: query
        type: integer
        default: 3
        description: The number of packets to send.
    security:
      - basicAuth: []
    responses:
      200:
        description: The output of the ping command.
      400:
        description: Bad request, missing host parameter.
    """
    host = request.args.get('host')
    count = request.args.get('count', '3')

    if not host:
        return jsonify({"error": "Missing host parameter"}), 400

    try:
        # Sanitize count to be an integer
        count = str(int(count))
    except ValueError:
        return jsonify({"error": "Invalid count parameter"}), 400

    # Basic input validation to prevent command injection
    if not all(c.isalnum() or c in '.-' for c in host):
        return jsonify({"error": "Invalid host parameter"}), 400

    try:
        output = subprocess.check_output(['ping', '-c', count, host], stderr=subprocess.STDOUT, universal_newlines=True)
        return Response(output, mimetype='text/plain')
    except subprocess.CalledProcessError as e:
        return Response(e.output, status=400, mimetype='text/plain')

@diag_bp.route('/api/dns', methods=['GET'])
@requires_auth
def dns_resolve():
    """
    Resolves DNS A/AAAA records for a given domain name.
    ---
    parameters:
      - name: name
        in: query
        type: string
        required: true
        description: The domain name to resolve.
    security:
      - basicAuth: []
    responses:
      200:
        description: A list of IP addresses.
      400:
        description: Bad request, missing name parameter or resolution failed.
    """
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Missing name parameter"}), 400

    # Basic input validation
    if not all(c.isalnum() or c in '.-' for c in name):
        return jsonify({"error": "Invalid name parameter"}), 400

    try:
        results = socket.getaddrinfo(name, None, proto=socket.IPPROTO_TCP)
        addresses = [res[4][0] for res in results]
        return jsonify({"addresses": list(set(addresses))})
    except socket.gaierror as e:
        return jsonify({"error": str(e)}), 400

@diag_bp.route('/api/curl', methods=['GET'])
@requires_auth
def curl():
    """
    Performs an HTTP GET request to the specified URL.
    ---
    parameters:
      - name: url
        in: query
        type: string
        required: true
        description: The URL to fetch.
    security:
      - basicAuth: []
    responses:
      200:
        description: The content of the URL.
      400:
        description: Bad request, missing url parameter or request failed.
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        response = requests.get(url, timeout=5)
        return Response(response.text, status=response.status_code, mimetype=response.headers.get('Content-Type'))
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

@diag_bp.route('/api/tcp-check', methods=['GET'])
@requires_auth
def tcp_check():
    """
    Attempts a TCP connection to the specified host and port.
    ---
    parameters:
      - name: host
        in: query
        type: string
        required: true
        description: The host to connect to.
      - name: port
        in: query
        type: integer
        required: true
        description: The port to connect to.
    security:
      - basicAuth: []
    responses:
      200:
        description: Connection successful.
      400:
        description: Bad request, missing parameters or connection failed.
    """
    host = request.args.get('host')
    port = request.args.get('port')

    if not host or not port:
        return jsonify({"error": "Missing host or port parameter"}), 400

    try:
        port = int(port)
    except ValueError:
        return jsonify({"error": "Invalid port parameter"}), 400

    # Basic input validation
    if not all(c.isalnum() or c in '.-' for c in host):
        return jsonify({"error": "Invalid host parameter"}), 400

    try:
        with socket.create_connection((host, port), timeout=5):
            return jsonify({"status": "success", "message": f"Successfully connected to {host}:{port}"})
    except (socket.timeout, socket.error) as e:
        return jsonify({"status": "failure", "message": str(e)}), 400

@diag_bp.route('/api/headers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@requires_auth
def echo_headers():
    """
    Echoes back the request headers.
    ---
    security:
      - basicAuth: []
    responses:
      200:
        description: The request headers.
    """
    return jsonify(dict(request.headers))

@diag_bp.route('/api/echo', methods=['POST', 'PUT'])
@requires_auth
def echo_body():
    """
    Echoes back the request body.
    ---
    security:
      - basicAuth: []
    responses:
      200:
        description: The request body.
    """
    return Response(request.get_data(), mimetype=request.mimetype)


@sock.route('/api/ws/echo')
def echo(ws):
    """
    Echoes back messages sent over a WebSocket connection.
    """
    while True:
        try:
            data = ws.receive()
            ws.send(data)
        except ConnectionClosed:
            break


@diag_bp.route('/api/random-error', methods=['GET'])
@requires_auth
def random_error():
    """
    Returns a random HTTP error status code.
    ---
    security:
      - basicAuth: []
    responses:
      400:
        description: Bad Request
      401:
        description: Unauthorized
      403:
        description: Forbidden
      404:
        description: Not Found
      500:
        description: Internal Server Error
      502:
        description: Bad Gateway
      503:
        description: Service Unavailable
      504:
        description: Gateway Timeout
    """
    error_codes = [400, 401, 403, 404, 500, 502, 503, 504]
    selected_code = random.choice(error_codes)
    return jsonify({"error": f"Randomly generated error: {selected_code}"}), selected_code
