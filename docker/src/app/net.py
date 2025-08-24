from flask import Blueprint, jsonify
import psutil
import time

net_bp = Blueprint('net', __name__)

@net_bp.route('/api/net/stats')
def net_stats():
    """
    Get network I/O statistics
    ---
    responses:
      200:
        description: A dictionary of network interface statistics
        schema:
          type: object
          properties:
            timestamp:
              type: number
            interfaces:
              type: object
              additionalProperties:
                type: object
                properties:
                  bytes_sent:
                    type: integer
                  bytes_recv:
                    type: integer
                  packets_sent:
                    type: integer
                  packets_recv:
                    type: integer
                  errin:
                    type: integer
                  errout:
                    type: integer
                  dropin:
                    type: integer
                  dropout:
                    type: integer
    """
    io_counters = psutil.net_io_counters(pernic=True)
    stats = {
        "timestamp": time.time(),
        "interfaces": {
            iface: {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout,
            }
            for iface, counters in io_counters.items()
        }
    }
    return jsonify(stats)
