# start_celery_worker.py
import os
from subprocess import call
from dotenv import load_dotenv

load_dotenv()

worker_hostname = os.getenv('CELERY_WORKER_HOSTNAME', 'fromedwin.worker')
concurrency = os.getenv('CELERYD_CONCURRENCY', '1')  # Default to 1 if not set
# Keep aligned with Django CELERY_QUEUE / task_default_queue
queue = os.getenv('CELERY_QUEUE', 'fromedwin_queue')

# Start Celery Worker with configurable concurrency
call([
    'celery', '-A', 'fromedwin', 'worker',
    '--loglevel=info',
    f'--hostname={worker_hostname}',
    f'--concurrency={concurrency}',
    f'--queues={queue}',
    '--prefetch-multiplier=1',  # Fetch only one task at a time from broker
])
