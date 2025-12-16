"""
Celery configuration for the customer support system.
"""
import os

from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('customer_support')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')

