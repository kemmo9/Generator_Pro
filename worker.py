import os
import redis
from rq import Worker, Queue

# THIS IS THE NEW IMPORT LINE
import tasks

# The list of queues this worker will listen to.
listen = ['default']

# Get the Redis connection URL from the environment variable
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Establish the connection to Redis
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    # We create the list of queues, explicitly passing the connection to each Queue object.
    queues = [Queue(name, connection=conn) for name in listen]
    
    # Now we create the worker, which also needs the connection.
    worker = Worker(queues, connection=conn)
    
    # Start the worker process. It will now wait for jobs.
    worker.work()
