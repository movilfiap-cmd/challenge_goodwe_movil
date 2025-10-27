from django.core.management.base import BaseCommand
from django.utils import timezone
from consumption.tasks import update_device_consumption, update_solar_production, generate_complete_energy_reading


class Command(BaseCommand):
    help = 'Manually update device consumption readings based on their limits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['consumption', 'production', 'complete'],
            default='complete',
            help='Type of update to perform: consumption (devices only), production (solar only), or complete (both)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run the update asynchronously using Celery'
        )

    def handle(self, *args, **options):
        update_type = options['type']
        run_async = options['async']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting {update_type} consumption update...')
        )
        
        try:
            if run_async:
                # Run asynchronously using Celery
                if update_type == 'consumption':
                    task = update_device_consumption.delay()
                elif update_type == 'production':
                    task = update_solar_production.delay()
                else:  # complete
                    task = generate_complete_energy_reading.delay()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Task {task.id} queued successfully')
                )
                self.stdout.write('Use Celery monitoring tools to check task status')
                
            else:
                # Run synchronously
                if update_type == 'consumption':
                    result = update_device_consumption()
                elif update_type == 'production':
                    result = update_solar_production()
                else:  # complete
                    result = generate_complete_energy_reading()
                
                if result['status'] == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ {result['message']}")
                    )
                    
                    if update_type in ['consumption', 'complete']:
                        self.stdout.write(
                            f"📊 Devices updated: {result.get('devices_updated', 0)}"
                        )
                        self.stdout.write(
                            f"⚡ Total consumption: {result.get('total_consumption', 0):.2f} kWh"
                        )
                        if 'alerts_created' in result:
                            self.stdout.write(
                                f"🚨 Alerts created: {result['alerts_created']}"
                            )
                    
                    if update_type in ['production', 'complete']:
                        self.stdout.write(
                            f"☀️ Panels updated: {result.get('panels_updated', 0)}"
                        )
                        self.stdout.write(
                            f"🔋 Total production: {result.get('total_production', 0):.2f} kWh"
                        )
                    
                    if update_type == 'complete':
                        self.stdout.write(
                            f"⚖️ Net balance: {result.get('net_balance', 0):.2f} kWh"
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ {result['message']}")
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running consumption update: {str(e)}')
            )
