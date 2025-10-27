from celery import shared_task
from django.utils import timezone
from django.db import transaction
import random
import logging

from devices.models import Device, DevicePriority
from consumption.models import ConsumptionReading, ConsumptionAlert, SolarPanel, EnergyManagementConfig

logger = logging.getLogger(__name__)


@shared_task
def update_device_consumption():
    """
    Task to automatically update device consumption readings based on their limits.
    This task runs periodically to simulate real-time consumption data.
    """
    try:
        logger.info("Starting automatic consumption update...")
        
        # Get all active devices
        active_devices = Device.objects.filter(is_active=True)
        
        if not active_devices.exists():
            logger.warning("No active devices found for consumption update")
            return {
                'status': 'success',
                'message': 'No active devices found',
                'devices_updated': 0,
                'total_consumption': 0.0
            }
        
        generated_readings = []
        total_consumption = 0.0
        alerts_created = 0
        
        with transaction.atomic():
            for device in active_devices:
                # Generate consumption based on device's max_consumption (Limite Máximo)
                consumption_kwh = generate_realistic_consumption(device.max_consumption)
                
                # Create consumption reading
                reading = ConsumptionReading.objects.create(
                    device=device,
                    consumption_kwh=consumption_kwh,
                    production_kwh=0.0,  # Devices don't produce energy
                    timestamp=timezone.now()
                )
                
                # Update device's last consumption
                device.last_consumption = consumption_kwh
                device.save(update_fields=['last_consumption'])
                
                generated_readings.append({
                    'device_id': device.device_id,
                    'device_name': device.name,
                    'consumption_kwh': consumption_kwh,
                    'max_consumption': device.max_consumption,
                    'status': reading.get_consumption_status()
                })
                
                total_consumption += consumption_kwh
                
                # Create alert if consumption exceeds limit
                if consumption_kwh > device.max_consumption:
                    ConsumptionAlert.objects.create(
                        device=device,
                        alert_type='limit_exceeded',
                        severity='high',
                        message=f'Consumo de {consumption_kwh:.2f} kWh excedeu o limite de {device.max_consumption:.2f} kWh'
                    )
                    alerts_created += 1
                    logger.warning(f"Alert created for device {device.name}: consumption exceeded limit")
        
        logger.info(f"Consumption update completed: {len(generated_readings)} devices updated, {alerts_created} alerts created")
        
        return {
            'status': 'success',
            'message': 'Device consumption updated successfully',
            'devices_updated': len(generated_readings),
            'total_consumption': total_consumption,
            'alerts_created': alerts_created,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating device consumption: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error updating consumption: {str(e)}',
            'devices_updated': 0,
            'total_consumption': 0.0
        }


@shared_task
def update_solar_production():
    """
    Task to automatically update solar panel production readings.
    This task runs periodically to simulate real-time solar production data.
    """
    try:
        logger.info("Starting automatic solar production update...")
        
        # Get all active solar panels
        active_panels = SolarPanel.objects.filter(is_active=True)
        
        if not active_panels.exists():
            logger.warning("No active solar panels found for production update")
            return {
                'status': 'success',
                'message': 'No active solar panels found',
                'panels_updated': 0,
                'total_production': 0.0
            }
        
        total_production = 0.0
        
        with transaction.atomic():
            for panel in active_panels:
                # Get current production based on time and weather
                production_kwh = panel.get_current_production()
                
                # Create production reading (we need to create a dummy device for solar panels)
                # For now, we'll skip creating ConsumptionReading for solar panels
                # and create EnergyProduction records instead
                from consumption.models import EnergyProduction
                EnergyProduction.objects.create(
                    device=None,  # Solar panels are not consumption devices
                    production_kwh=production_kwh,
                    timestamp=timezone.now()
                )
                
                total_production += production_kwh
        
        logger.info(f"Solar production update completed: {active_panels.count()} panels updated")
        
        return {
            'status': 'success',
            'message': 'Solar production updated successfully',
            'panels_updated': active_panels.count(),
            'total_production': total_production,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating solar production: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error updating solar production: {str(e)}',
            'panels_updated': 0,
            'total_production': 0.0
        }


@shared_task
def generate_complete_energy_reading():
    """
    Combined task that updates both device consumption and solar production.
    This is the main task that should be scheduled to run periodically.
    """
    try:
        logger.info("Starting complete energy reading generation...")
        
        # Update device consumption
        consumption_result = update_device_consumption()
        
        # Update solar production
        production_result = update_solar_production()
        
        # Check for deficit and control devices automatically
        control_result = check_and_control_devices()
        
        # Calculate net balance
        net_balance = production_result.get('total_production', 0.0) - consumption_result.get('total_consumption', 0.0)
        
        logger.info(f"Complete energy reading generated: Net balance = {net_balance:.2f} kWh")
        
        return {
            'status': 'success',
            'message': 'Complete energy reading generated successfully',
            'consumption': consumption_result,
            'production': production_result,
            'control': control_result,
            'net_balance': net_balance,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating complete energy reading: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error generating energy reading: {str(e)}',
            'consumption': {'devices_updated': 0, 'total_consumption': 0.0},
            'production': {'panels_updated': 0, 'total_production': 0.0},
            'net_balance': 0.0
        }


def generate_realistic_consumption(max_consumption):
    """
    Generate realistic consumption values based on device's maximum consumption limit.
    
    Args:
        max_consumption (float): The device's maximum consumption limit (Limite Máximo)
    
    Returns:
        float: Generated consumption value in kWh
    """
    # 70% of the time: normal consumption (0.3 to 0.9 of limit)
    # 20% of the time: high consumption (0.9 to 1.1 of limit)  
    # 10% of the time: very high consumption (1.1 to 1.3 of limit)
    
    rand = random.random()
    
    if rand < 0.7:
        # Normal consumption
        consumption_factor = random.uniform(0.3, 0.9)
    elif rand < 0.9:
        # High consumption (occasionally exceeds limit)
        consumption_factor = random.uniform(0.9, 1.1)
    else:
        # Very high consumption (exceeds limit)
        consumption_factor = random.uniform(1.1, 1.3)
    
    # Calculate base consumption
    base_consumption = max_consumption * consumption_factor
    
    # Add realistic variation using Gaussian distribution (±5%)
    variation = random.gauss(0, base_consumption * 0.05)
    final_consumption = base_consumption + variation
    
    # Ensure consumption is never negative
    return max(0.0, final_consumption)


@shared_task
def cleanup_old_readings():
    """
    Task to clean up old consumption readings to prevent database bloat.
    Keeps only the last 30 days of readings.
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Count readings to be deleted
        old_readings_count = ConsumptionReading.objects.filter(
            timestamp__lt=cutoff_date
        ).count()
        
        # Delete old readings
        deleted_count, _ = ConsumptionReading.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old consumption readings")
        
        return {
            'status': 'success',
            'message': f'Cleaned up {deleted_count} old readings',
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old readings: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error cleaning up readings: {str(e)}',
            'deleted_count': 0
        }


@shared_task
def check_and_control_devices():
    """
    Verifica se há déficit de produção e controla dispositivos automaticamente
    baseado na prioridade configurada.
    """
    try:
        logger.info("Starting automatic device control check...")
        
        # Obter configuração ativa
        config = EnergyManagementConfig.get_active_config()
        if not config or not config.auto_control_enabled:
            logger.info("Auto control is disabled or no active config found")
            return {
                'status': 'skipped',
                'message': 'Auto control is disabled or no active config found',
                'devices_controlled': 0,
                'alerts_created': 0
            }
        
        # Obter leituras mais recentes
        latest_reading = ConsumptionReading.objects.order_by('-timestamp').first()
        if not latest_reading:
            logger.warning("No consumption readings found")
            return {
                'status': 'skipped',
                'message': 'No consumption readings found',
                'devices_controlled': 0,
                'alerts_created': 0
            }
        
        # Calcular produção atual total
        total_production = latest_reading.production_kwh
        
        # Calcular consumo atual total (apenas dispositivos ativos)
        active_devices = Device.objects.filter(is_active=True)
        total_consumption = sum(device.last_consumption for device in active_devices)
        
        # Calcular percentual de produção vs consumo
        if total_consumption > 0:
            production_percentage = (total_production / total_consumption) * 100
        else:
            production_percentage = 100.0  # Se não há consumo, considerar 100%
        
        logger.info(f"Production: {total_production:.2f} kWh, Consumption: {total_consumption:.2f} kWh, Percentage: {production_percentage:.2f}%")
        
        # Verificar se há déficit
        deficit_threshold = config.deficit_threshold_percentage
        is_deficit = production_percentage < deficit_threshold
        
        devices_controlled = 0
        alerts_created = 0
        
        if is_deficit:
            logger.warning(f"Production deficit detected: {production_percentage:.2f}% < {deficit_threshold}%")
            
            # Criar alerta de déficit detectado
            ConsumptionAlert.objects.create(
                device=None,  # Alerta geral, não específico de dispositivo
                alert_type='deficit_detected',
                severity='high',
                message=f'Déficit de produção detectado: {production_percentage:.2f}% < {deficit_threshold}%'
            )
            alerts_created += 1
            
            with transaction.atomic():
                # Controlar dispositivos de prioridade BAIXA automaticamente
                baixa_devices = active_devices.filter(priority=DevicePriority.BAIXA)
                
                for device in baixa_devices:
                    if device.is_controllable:
                        # Tentar controlar dispositivo Tuya
                        success = control_tuya_device(device, False)  # False = turn off
                        if success:
                            device.is_active = False
                            device.auto_controlled = True
                            device.auto_control_timestamp = timezone.now()
                            device.save()
                            
                            # Criar alerta de dispositivo controlado
                            ConsumptionAlert.objects.create(
                                device=device,
                                alert_type='device_auto_controlled',
                                severity='medium',
                                message=f'Dispositivo {device.name} foi desligado automaticamente devido ao déficit de produção'
                            )
                            alerts_created += 1
                            devices_controlled += 1
                            logger.info(f"Device {device.name} turned off automatically")
                        else:
                            logger.warning(f"Failed to control device {device.name}")
                    else:
                        # Para dispositivos não controláveis, apenas marcar como sugerido para desligar
                        device.auto_controlled = True
                        device.auto_control_timestamp = timezone.now()
                        device.save()
                        
                        ConsumptionAlert.objects.create(
                            device=device,
                            alert_type='device_auto_controlled',
                            severity='medium',
                            message=f'Dispositivo {device.name} deve ser desligado manualmente devido ao déficit de produção'
                        )
                        alerts_created += 1
                        devices_controlled += 1
                        logger.info(f"Device {device.name} marked for manual control")
                
                # Criar alertas para dispositivos de prioridade MÉDIA
                media_devices = active_devices.filter(priority=DevicePriority.MEDIA)
                
                for device in media_devices:
                    ConsumptionAlert.objects.create(
                        device=device,
                        alert_type='medium_priority_action_needed',
                        severity='high',
                        message=f'Dispositivo {device.name} (prioridade média) precisa de decisão do usuário devido ao déficit de produção'
                    )
                    alerts_created += 1
                    logger.info(f"Alert created for medium priority device {device.name}")
        
        logger.info(f"Device control check completed: {devices_controlled} devices controlled, {alerts_created} alerts created")
        
        return {
            'status': 'success',
            'message': 'Device control check completed',
            'production_percentage': production_percentage,
            'deficit_threshold': deficit_threshold,
            'is_deficit': is_deficit,
            'devices_controlled': devices_controlled,
            'alerts_created': alerts_created,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in device control check: {str(e)}")
        return {
            'status': 'error',
            'message': f'Error in device control check: {str(e)}',
            'devices_controlled': 0,
            'alerts_created': 0
        }


def control_tuya_device(device, turn_on=True):
    """
    Controla um dispositivo Tuya (liga/desliga).
    
    Args:
        device: Instância do Device
        turn_on: True para ligar, False para desligar
    
    Returns:
        bool: True se o controle foi bem-sucedido
    """
    try:
        if device.device_type != 'tuya':
            logger.warning(f"Device {device.name} is not a Tuya device")
            return False
        
        # Para ambiente de teste, simular controle bem-sucedido
        # Em produção, aqui seria feita a chamada real para a API Tuya
        logger.info(f"Simulating Tuya control for device {device.name}: {'ON' if turn_on else 'OFF'}")
        
        # Simular delay de rede
        import time
        time.sleep(0.1)
        
        return True
        
    except Exception as e:
        logger.error(f"Error controlling Tuya device {device.name}: {str(e)}")
        return False
