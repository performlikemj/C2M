# c2m_gym/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'c2m_gym.settings')

app = Celery('c2m_gym')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Set the timezone for Celery
app.conf.timezone = 'Asia/Tokyo'

app.conf.beat_schedule = {
    'check-active-subscriptions-daily': {
        'task': 'gymApp.tasks.check_active_subscriptions',
        'schedule': crontab(hour=9, minute=0),  # Schedule to run daily at 9 AM JST
    },
    'check-membership-periods-monthly': {
        'task': 'gymApp.tasks.check_and_update_membership_periods',
        'schedule': crontab(0, 0, day_of_month='1'),  # Run at midnight on the 1st of every month
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
