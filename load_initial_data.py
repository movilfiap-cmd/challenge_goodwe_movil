#!/usr/bin/env python
"""
Script para carregar dados iniciais do arquivo CSV.
"""

import os
import sys
import django
import csv
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energy_manager.settings')
django.setup()

from devices.models import Device, DeviceStatus
from consumption.models import ConsumptionReading
from django.contrib.auth.models import User

def load_csv_data():
    """Carrega dados do arquivo CSV para o banco de dados."""
    csv_path = 'leituras_sim.csv'
    
    if not os.path.exists(csv_path):
        print(f"❌ Arquivo {csv_path} não encontrado!")
        return
    
    print("📊 Carregando dados do CSV...")
    
    # Criar usuário padrão se não existir
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
        print("👤 Usuário admin criado (senha: admin123)")
    
    # Ler dados do CSV
    devices_data = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                device_id = row.get('device_id') or row.get('Device')
                if not device_id:
                    continue
                
                try:
                    consumption = float(row.get('consumo_kwh') or row.get('consumo') or 0)
                except ValueError:
                    consumption = 0.0
                
                timestamp_str = row.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                # Agrupar por dispositivo
                if device_id not in devices_data:
                    devices_data[device_id] = {
                        'name': device_id,
                        'device_id': device_id,
                        'last_consumption': consumption,
                        'readings': []
                    }
                
                devices_data[device_id]['readings'].append({
                    'consumption': consumption,
                    'timestamp': timestamp
                })
                
                # Atualizar último consumo
                if consumption > devices_data[device_id]['last_consumption']:
                    devices_data[device_id]['last_consumption'] = consumption
        
        # Criar dispositivos
        created_devices = 0
        for device_id, data in devices_data.items():
            device, created = Device.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'name': data['name'],
                    'device_type': 'manual',
                    'last_consumption': data['last_consumption'],
                    'max_consumption': 10.0,
                    'is_active': True,
                    'created_by': user
                }
            )
            
            if created:
                created_devices += 1
                
                # Criar status do dispositivo
                DeviceStatus.objects.create(
                    device=device,
                    is_online=True,
                    last_seen=datetime.now()
                )
                
                # Criar leituras de consumo
                for reading in data['readings']:
                    ConsumptionReading.objects.create(
                        device=device,
                        timestamp=reading['timestamp'],
                        consumption_kwh=reading['consumption']
                    )
        
        print(f"✅ {created_devices} dispositivos criados com sucesso!")
        print(f"📈 {sum(len(data['readings']) for data in devices_data.values())} leituras de consumo importadas!")
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")

def main():
    """Função principal."""
    print("🚀 Carregando dados iniciais do Energy Manager...")
    load_csv_data()
    print("✅ Dados iniciais carregados com sucesso!")

if __name__ == '__main__':
    main()
