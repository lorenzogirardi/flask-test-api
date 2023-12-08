#!flask/bin/python
import time
from flask import Flask, jsonify, abort, request, make_response, url_for, render_template
from prometheus_flask_exporter import PrometheusMetrics
import logging
from flask_compress import Compress
from redis import Redis
from os import getenv
import requests
from flask import Response
from requests import get
from flask_zipkin import Zipkin


app = Flask(__name__, static_url_path = "")
metrics = PrometheusMetrics(app)
Compress(app)

zipkin = Zipkin(app, sample_rate=100)


REDIS_HOST = getenv("REDIS_HOST", default="localhost")
REDIS_PORT = getenv("REDIS_PORT", default=6379)
REDIS_DB = getenv("REDIS_DB", default=0)
r = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
SITE_NAME = 'http://webdis-svc.webdis:7379'

logging.basicConfig(
	level=logging.INFO, 
	format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
	handlers=[
     	   logging.FileHandler("/var/log/app.log"),
           logging.StreamHandler()
    ]
)

    
@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

context = [
    {
        'id': 1,
        'title': u'Cento 6',
        'description': u'RHEL 6 based', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Centos 7',
        'description': u'RHEL 7 based', 
        'done': False
    },
    {
        'id': 3,
        'title': u'Centos 8',
        'description': u'RHEL 8 based', 
        'done': False
    },
    {
        'id': 4,
        'title': u'Centos stream',
        'description': u'Fedora + RHEL based', 
        'done': False
    }
]

@app.route('/api/')
def index():
    return render_template('index.html')

def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id = task['id'], _external = True)
        else:
            new_task[field] = task[field]
    return new_task
    
@app.route('/api/get/context', methods = ['GET'])
def get_context():
    return jsonify( { 'context': list(map(make_public_task, context)) } )


@app.route('/api/get/context/<int:task_id>', methods = ['GET'])
def get_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, context))
    if len(task) == 0:
        abort(404)
    return jsonify( { 'task': make_public_task(task[0]) } )

@app.route('/api/post/context', methods = ['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': context[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    context.append(task)
    return jsonify( { 'task': make_public_task(task) } ), 201

@app.route('/api/put/context/<int:task_id>', methods = ['PUT'])
def update_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, context))
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != str:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not str:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify( { 'task': make_public_task(task[0]) } )
    
@app.route('/api/delete/context/<int:task_id>', methods = ['DELETE'])
def delete_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, context))
    if len(task) == 0:
        abort(404)
    context.remove(task[0])
    return jsonify( { 'result': True } )

@app.route('/api/fib/<int:x>')
def fib(x):
    return str(calcfib(x))
def calcfib(n):
    if n == 0:
        return 0
    b, a = 0, 1             # b, a initialized as F(0), F(1)
    for i in range(1,n) :
        b, a = a, a+b       # b, a always store F(i-1), F(i) 
    return a

@app.route('/api/sleep/<int:x>')
def delay(x):
    time.sleep(x)
    return "delayed by " +(str(x)) +" seconds"

@app.route('/api/count')
def count():
    r.incr('hits')
    counter = str(r.get('hits'),'utf-8')
    return counter

#@app.route('/api/redisping')
#def ping():
#    wd = requests.get("http://webdis-svc.webdis:7379/PING")
#    return Response(
#        wd.text,
#        status=wd.status_code,
#    )
 
@app.route('/api/redisping')
def proxy():
    headers = {}
    headers.update(zipkin.create_http_headers_for_new_span())
    return get(f'{SITE_NAME}/ping', headers=headers).content
   
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
