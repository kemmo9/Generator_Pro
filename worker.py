# The final, correct worker script.

import os
import redis
from rq import Worker, Queue

# THIS IS THE MOST IMPORTANT LINE:
# By importing the tasks module, we make all the functions inside tasks.py
# discoverable by the worker process when it receives a job by its string name.
import tasks

# The list of queues this worker will listen to.
listen = ['default']

# Get the Redis connection URL from the environment variable
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Establish the connection to Redis
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    # Create the list of queues, explicitly passing the connection to each Queue object.
    queues = [Queue(name, connection=conn) for name in listen]
    
    # Create the worker, which also needs the connection.
    worker = Worker(queues, connection=conn)
    
    # Start the worker process. It will now wait for jobs.
    worker.work()
