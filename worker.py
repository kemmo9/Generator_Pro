import os
import redis
from rq import Connection, Worker

# This is the crucial part that was missing.
# It tells the worker to listen on the default queue.
listen = ['default']

# Get the Redis URL from the environment variables provided by Render.
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    # When this script is run, create a connection and start a worker.
    # The worker will now correctly import and run jobs from tasks.py
    with Connection(conn):
        worker = Worker(map(str, listen))
        worker.work()
