# app/celery_config.py

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue
import os
from app.core.config import settings

# Create Celery app
celery_app = Celery(__name__)

# Redis as broker
# Use settings if available, otherwise fallback to env or default
REDIS_URL = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL

# Task settings
celery_app.conf.task_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.result_serializer = 'json'
celery_app.conf.timezone = 'UTC'
celery_app.conf.enable_utc = True

# Define queues
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('email', Exchange('email'), routing_key='email.#'),
    Queue('follow_ups', Exchange('follow_ups'), routing_key='follow_ups.#'),
    Queue('routing', Exchange('routing'), routing_key='routing.#'),
)

# Define routes
celery_app.conf.task_routes = {
    'app.domains.email_ai.workers.auto_organize.auto_organize_inbox': {'queue': 'email'},
    'app.domains.email_ai.workers.follow_up.check_follow_ups': {'queue': 'follow_ups'},
    'tasks.route_and_allocate_email': {'queue': 'routing'},
}

# Beat schedule
celery_app.conf.beat_schedule = {
    'auto-organize-inbox': {
        'task': 'app.domains.email_ai.workers.auto_organize.auto_organize_inbox',
        'schedule': 5.0,  # Every 5 seconds
        # Note: In a real system, we would iterate over users. 
        # For now, we'll need a mechanism to pass user_id/gmail_user_id.
        'args': ('default_user', 'me'), 
        'options': {'queue': 'email'}
    },
    'check-follow-ups': {
        'task': 'app.domains.email_ai.workers.follow_up.check_follow_ups',
        'schedule': crontab(minute=0),  # Every hour
        'options': {'queue': 'follow_ups'}
    },
}

# Task time limits
celery_app.conf.task_time_limit = 30 * 60  # 30 minutes hard limit
celery_app.conf.task_soft_time_limit = 25 * 60  # 25 minutes soft limit

# Explicitly import task modules
celery_app.conf.imports = [
    'app.domains.email_ai.workers.auto_organize',
    'app.domains.email_ai.workers.follow_up',
    'app.domains.email_ai.workers.routing',
]
