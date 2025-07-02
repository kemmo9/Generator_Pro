import os
import redis
from rq import Worker, Queue, Connection

# Define the queues to listen to. 'default' is the standard queue.
listen = ['default']

# Get the Redis URL from the environment variables provided by Render.
# Fallback to a local Redis instance for testing if needed.
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Establish a connection to the Redis server.
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    # Use a Connection context manager to ensure the connection is handled correctly.
    with Connection(conn):
        # Create a Worker instance that listens on the specified queues.
        worker = Worker(map(Queue, listen))
        
        # Start the worker. It will now wait for and execute jobs from the queue.
        # This is a blocking call, the script will run here indefinitely.
        worker.work()
