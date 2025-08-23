from flask import Flask, jsonify, request, make_response, render_template
from flask_compress import Compress
from prometheus_flask_exporter import PrometheusMetrics
from ddtrace import tracer
from flasgger import Swagger
from .utils import get_redis_connection
from .health import health_bp
from . import business
import logging
import json

# Initialize Flask App
app = Flask(__name__)
app.register_blueprint(health_bp)
swagger = Swagger(app)
Compress(app)
metrics = PrometheusMetrics(app)

# Setup logging
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(json.dumps({
    'timestamp': '%(asctime)s',
    'level': '%(levelname)s',
    'message': '%(message)s'
})))
logging.basicConfig(level=logging.INFO, handlers=[handler])

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# Routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/contexts', methods=['GET'])
def get_contexts():
    """
    Get all contexts
    ---
    responses:
      200:
        description: A list of contexts
        schema:
          type: array
          items:
            $ref: '#/definitions/Context'
    """
    contexts = business.get_all_contexts()
    return jsonify(contexts)

@app.route('/api/contexts/<string:context_id>', methods=['GET'])
def get_context(context_id):
    """
    Get a specific context
    ---
    parameters:
      - name: context_id
        in: path
        type: string
        required: true
    definitions:
      Context:
        type: object
        properties:
          id:
            type: string
          title:
            type: string
          description:
            type: string
          done:
            type: boolean
    responses:
      200:
        description: The context
        schema:
          $ref: '#/definitions/Context'
      404:
        description: Context not found
    """
    context = business.get_context_by_id(context_id)
    if not context:
        return make_response(jsonify({'error': 'Not found'}), 404)
    return jsonify(context)

@app.route('/api/contexts', methods=['POST'])
def create_context():
    """
    Create a new context
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: ContextPost
          required:
            - title
          properties:
            title:
              type: string
            description:
              type: string
    responses:
      201:
        description: The created context
        schema:
          $ref: '#/definitions/Context'
      400:
        description: Bad request
    """
    if not request.json:
        return make_response(jsonify({'error': 'Bad request'}), 400)
    context = business.create_new_context(request.json)
    if not context:
        return make_response(jsonify({'error': 'Bad request'}), 400)
    return make_response(jsonify(context), 201)

@app.route('/api/contexts/<string:context_id>', methods=['PUT'])
def update_context(context_id):
    """
    Update a context
    ---
    parameters:
      - name: context_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          id: ContextPut
          properties:
            title:
              type: string
            description:
              type: string
            done:
              type: boolean
    responses:
      200:
        description: The updated context
        schema:
          $ref: '#/definitions/Context'
      400:
        description: Bad request
      404:
        description: Context not found
    """
    if not request.json:
        return make_response(jsonify({'error': 'Bad request'}), 400)
    context = business.update_existing_context(context_id, request.json)
    if not context:
        return make_response(jsonify({'error': 'Not found'}), 404)
    return jsonify(context)

@app.route('/api/contexts/<string:context_id>', methods=['DELETE'])
def delete_context(context_id):
    """
    Delete a context
    ---
    parameters:
      - name: context_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Deletion result
        schema:
          type: object
          properties:
            result:
              type: boolean
      404:
        description: Context not found
    """
    if not business.delete_context_by_id(context_id):
        return make_response(jsonify({'error': 'Not found'}), 404)
    return jsonify({'result': True})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
