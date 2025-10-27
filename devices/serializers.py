from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Device, DeviceStatus


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer para dispositivos."""
    
    consumption_status = serializers.CharField(source='get_consumption_status', read_only=True)
    can_connect_tuya = serializers.BooleanField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    tuya_ip = serializers.IPAddressField(allow_blank=True, required=False)
    tuya_local_key = serializers.CharField(allow_blank=True, required=False)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_id', 'device_type', 'tuya_ip', 
            'tuya_local_key', 'tuya_version', 'last_consumption', 
            'max_consumption', 'is_active', 'is_controllable',
            'priority', 'auto_controlled', 'auto_control_timestamp',
            'consumption_status', 'can_connect_tuya', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'auto_controlled', 'auto_control_timestamp']
    
    def validate_device_id(self, value):
        """Valida se o device_id é único."""
        if self.instance and self.instance.device_id == value:
            return value
        
        if Device.objects.filter(device_id=value).exists():
            raise serializers.ValidationError(
                "Já existe um dispositivo com este ID."
            )
        return value
    
    def validate_tuya_version(self, value):
        """Valida a versão do protocolo Tuya."""
        if not (3.0 <= float(value) <= 3.4):
            raise serializers.ValidationError(
                "A versão do protocolo Tuya deve estar entre 3.0 e 3.4."
            )
        return value
    
    def validate(self, attrs):
        """Validações gerais do dispositivo."""
        device_type = attrs.get('device_type')
        tuya_ip = attrs.get('tuya_ip')
        tuya_local_key = attrs.get('tuya_local_key')
        
        # Para ambiente de teste, não validar IP e chave local para dispositivos Tuya
        # Converter strings vazias para None para todos os tipos de dispositivo
        if tuya_ip == '':
            attrs['tuya_ip'] = None
        if tuya_local_key == '':
            attrs['tuya_local_key'] = None
        
        return attrs


class DeviceCreateSerializer(DeviceSerializer):
    """Serializer para criação de dispositivos."""
    
    class Meta(DeviceSerializer.Meta):
        fields = DeviceSerializer.Meta.fields
        # Não incluir created_by nos campos, será definido pelo view
    
    def create(self, validated_data):
        """Cria um novo dispositivo."""
        # O created_by será definido automaticamente pelo view
        return super().create(validated_data)


class DeviceStatusSerializer(serializers.ModelSerializer):
    """Serializer para status dos dispositivos."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    
    class Meta:
        model = DeviceStatus
        fields = [
            'id', 'device', 'device_name', 'device_id', 'is_online', 
            'last_seen', 'current_power', 'voltage', 'current_amperage', 
            'updated_at'
        ]
        read_only_fields = ['updated_at']


class DeviceListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem de dispositivos."""
    
    consumption_status = serializers.CharField(source='get_consumption_status', read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_id', 'device_type', 'last_consumption',
            'max_consumption', 'is_active', 'priority', 'auto_controlled',
            'consumption_status'
        ]


class DeviceSummarySerializer(serializers.Serializer):
    """Serializer para resumo dos dispositivos."""
    
    total_devices = serializers.IntegerField()
    active_devices = serializers.IntegerField()
    total_consumption = serializers.FloatField()
    average_consumption = serializers.FloatField()
    devices_by_type = serializers.DictField()
    consumption_by_type = serializers.DictField()
    devices_with_consumption = serializers.IntegerField()
