import os
import redis
from rq import Worker, Queue

# The list of queues this worker will listen to.
listen = ['default']

# Get the Redis connection URL from the environment variable
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Establish the connection to Redis
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    # Create the list of Queue objects
    queues = list(map(Queue, listen))
    
    # Create the Worker and pass the queues and connection directly
    # This is the modern, correct pattern.
    worker = Worker(queues, connection=conn)
    
    # Start the worker process. It will now wait for jobs.
    worker.work()
