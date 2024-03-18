from flask import Flask, jsonify, abort, request, make_response, url_for, render_template
from flask_compress import Compress
from prometheus_flask_exporter import PrometheusMetrics
from redis import Redis
import logging
from os import getenv
import requests
import time  # Added this import for time module

app = Flask(__name__, static_url_path="")
metrics = PrometheusMetrics(app)
Compress(app)

# Configurations
REDIS_HOST = getenv("REDIS_HOST", default="localhost")
REDIS_PORT = int(getenv("REDIS_PORT", default=6379))
REDIS_DB = int(getenv("REDIS_DB", default=0))
SITE_NAME = 'http://webdis-svc.webdis:7379'

# Redis connection
r = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
    handlers=[
        logging.FileHandler("/var/log/app.log"),
        logging.StreamHandler()
    ]
)

# Sample data
context = [
    {'id': 1, 'title': 'Cento 6', 'description': 'RHEL 6 based', 'done': False},
    {'id': 2, 'title': 'Centos 7', 'description': 'RHEL 7 based', 'done': False},
    {'id': 3, 'title': 'Centos 8', 'description': 'RHEL 8 based', 'done': False},
    {'id': 4, 'title': 'Centos stream', 'description': 'Fedora + RHEL based', 'done': False}
]

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# Helper functions
def make_public_task(task):
    return {'uri': url_for('get_task', task_id=task['id'], _external=True), **task}

# Routes
@app.route('/api/')
def index():
    return render_template('index.html')

@app.route('/api/get/context', methods=['GET'])
def get_context():
    return jsonify({'context': [make_public_task(task) for task in context]})

@app.route('/api/get/context/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = next((task for task in context if task['id'] == task_id), None)
    if not task:
        abort(404)
    return jsonify({'task': make_public_task(task)})

@app.route('/api/post/context', methods=['POST'])
def create_task():
    if not request.json or 'title' not in request.json:
        abort(400)
    task = {
        'id': context[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    context.append(task)
    return jsonify({'task': make_public_task(task)}), 201

@app.route('/api/put/context/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = next((task for task in context if task['id'] == task_id), None)
    if not task:
        abort(404)
    if not request.json:
        abort(400)
    for field in ['title', 'description', 'done']:
        if field in request.json and type(request.json[field]) != type(task[field]):
            abort(400)
    task.update(request.json)
    return jsonify({'task': make_public_task(task)})

@app.route('/api/delete/context/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = next((task for task in context if task['id'] == task_id), None)
    if not task:
        abort(404)
    context.remove(task)
    return jsonify({'result': True})

@app.route('/api/fib/<int:x>')
def fib(x):
    return str(calcfib(x))

def calcfib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

@app.route('/api/sleep/<int:x>')
def delay(x):
    time.sleep(x)
    return f"Delayed by {x} seconds"

@app.route('/api/count')
def count():
    r.incr('hits')
    counter = r.get('hits').decode('utf-8')
    return counter

@app.route('/api/redisping')
def proxy():
    return requests.get(f'{SITE_NAME}/ping').content

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
