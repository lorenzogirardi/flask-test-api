import redis
from os import getenv
from flask_sock import Sock

sock = Sock()

def get_redis_connection():
    redis_host = getenv("REDIS_HOST", "localhost")
    redis_port = int(getenv("REDIS_PORT", 6379))
    redis_db = int(getenv("REDIS_DB", 0))
    return redis.Redis(host=redis_host, port=redis_port, db=redis_db)
