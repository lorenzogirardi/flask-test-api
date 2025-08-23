from flask import Blueprint, jsonify
from .utils import get_redis_connection

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Application is healthy
      503:
        description: Application is unhealthy
    """
    try:
        r = get_redis_connection()
        r.ping()
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'reason': str(e)}), 503
