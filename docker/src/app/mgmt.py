import os
import sys
import threading
import traceback
from flask import Blueprint, jsonify, current_app
from .utils import get_redis_connection

mgmt_bp = Blueprint('mgmt', __name__)

# --- Health Endpoint ---
@mgmt_bp.route('/mgmt/health')
def health_check():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Application is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: UP
            checks:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                  status:
                    type: string
      503:
        description: Application is unhealthy
    """
    checks = []
    app_status = "UP"

    # Check Redis connection
    try:
        r = get_redis_connection()
        r.ping()
        checks.append({"name": "redis", "status": "UP"})
    except Exception as e:
        checks.append({"name": "redis", "status": "DOWN", "error": str(e)})
        app_status = "DOWN"

    # Overall status
    response = jsonify({
        "status": app_status,
        "checks": checks
    })

    if app_status == "DOWN":
        return response, 503
    return response, 200

# --- Info Endpoint ---
@mgmt_bp.route('/mgmt/info')
def app_info():
    """
    Displays application information
    ---
    responses:
      200:
        description: Application information
    """
    return jsonify({
        "app": {
            "name": "pytbak",
            "description": "Python REST API Test Application",
            "version": "1.0.0"
        }
    })

# --- Env Endpoint ---
@mgmt_bp.route('/mgmt/env')
def app_env():
    """
    Displays whitelisted environment variables
    ---
    responses:
      200:
        description: Environment variables
    """
    SAFE_ENV_VARS = [
        'PATH', 'HOSTNAME', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB',
        'DD_PROFILING_ENABLED', 'DD_LOGS_INJECTION'
    ]

    safe_vars = {key: value for key, value in os.environ.items() if key in SAFE_ENV_VARS}
    return jsonify(safe_vars)

# --- Mappings Endpoint ---
@mgmt_bp.route('/mgmt/mappings')
def app_mappings():
    """
    Displays all URL mappings
    ---
    responses:
      200:
        description: A list of all URL mappings
    """
    rules = []
    for rule in current_app.url_map.iter_rules():
        rules.append({
            "endpoint": rule.endpoint,
            "methods": sorted(list(rule.methods)),
            "rule": rule.rule
        })
    return jsonify({"mappings": rules})

# --- Thread Dump Endpoint ---
@mgmt_bp.route('/mgmt/threaddump')
def app_threaddump():
    """
    Provides a thread dump
    ---
    responses:
      200:
        description: A thread dump
        content:
          text/plain:
            schema:
              type: string
    """
    dump = []
    for threadId, stack in sys._current_frames().items():
        dump.append(f"\n# Thread: {threadId}")
        for filename, lineno, name, line in traceback.extract_stack(stack):
            dump.append(f'  File: "{filename}", line {lineno}, in {name}')
            if line:
                dump.append(f"    {line.strip()}")
    return "\n".join(dump), 200, {'Content-Type': 'text/plain'}

# --- Metrics Endpoint Link ---
@mgmt_bp.route('/mgmt/metrics')
def app_metrics_link():
    """
    Provides a link to the main /metrics endpoint
    ---
    responses:
      200:
        description: A link to the Prometheus metrics endpoint
    """
    return jsonify({
        "message": "Metrics are available at the /metrics endpoint.",
        "_links": {
            "self": {"href": "/mgmt/metrics"},
            "metrics": {"href": "/metrics"}
        }
    })
