import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energy_manager.settings')

app = Celery('energy_manager')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic task configuration
app.conf.beat_schedule = {
    # Update device consumption every 5 minutes
    'update-device-consumption': {
        'task': 'consumption.tasks.update_device_consumption',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    # Update solar production every 5 minutes
    'update-solar-production': {
        'task': 'consumption.tasks.update_solar_production',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    # Generate complete energy reading every 5 minutes
    'generate-complete-energy-reading': {
        'task': 'consumption.tasks.generate_complete_energy_reading',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    # Clean up old readings daily at 2 AM
    'cleanup-old-readings': {
        'task': 'consumption.tasks.cleanup_old_readings',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

# Timezone configuration
app.conf.timezone = 'America/Sao_Paulo'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
