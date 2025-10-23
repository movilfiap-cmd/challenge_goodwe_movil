from rest_framework import serializers
from django.utils import timezone
from .models import ConsumptionReading, ConsumptionLimit, ConsumptionAlert
from devices.models import Device


class ConsumptionReadingSerializer(serializers.ModelSerializer):
    """Serializer para leituras de consumo."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    consumption_status = serializers.CharField(source='get_consumption_status', read_only=True)
    
    class Meta:
        model = ConsumptionReading
        fields = [
            'id', 'device', 'device_name', 'device_id', 'timestamp', 
            'consumption_kwh', 'power_watts', 'voltage', 'current_amperage',
            'consumption_status', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def validate_consumption_kwh(self, value):
        """Valida o consumo em kWh."""
        if value < 0:
            raise serializers.ValidationError("Consumo não pode ser negativo.")
        return value
    
    def validate_timestamp(self, value):
        """Valida o timestamp da leitura."""
        if value > timezone.now():
            raise serializers.ValidationError("Timestamp não pode ser no futuro.")
        return value


class ConsumptionReadingCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de leituras de consumo."""
    
    class Meta:
        model = ConsumptionReading
        fields = [
            'device', 'timestamp', 'consumption_kwh', 'power_watts', 
            'voltage', 'current_amperage'
        ]
    
    def create(self, validated_data):
        """Cria uma nova leitura e atualiza o consumo do dispositivo."""
        reading = super().create(validated_data)
        
        # Atualizar o último consumo do dispositivo
        device = reading.device
        device.last_consumption = reading.consumption_kwh
        device.save()
        
        return reading


class ConsumptionLimitSerializer(serializers.ModelSerializer):
    """Serializer para limites de consumo."""
    
    effective_limit = serializers.FloatField(source='get_effective_limit', read_only=True)
    
    class Meta:
        model = ConsumptionLimit
        fields = [
            'id', 'name', 'base_limit_kwh', 'weather_factor', 
            'effective_limit', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_base_limit_kwh(self, value):
        """Valida o limite base."""
        if value <= 0:
            raise serializers.ValidationError("Limite base deve ser positivo.")
        return value
    
    def validate_weather_factor(self, value):
        """Valida o fator meteorológico."""
        if value <= 0:
            raise serializers.ValidationError("Fator meteorológico deve ser positivo.")
        return value


class ConsumptionAlertSerializer(serializers.ModelSerializer):
    """Serializer para alertas de consumo."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    
    class Meta:
        model = ConsumptionAlert
        fields = [
            'id', 'device', 'device_name', 'device_id', 'alert_type', 
            'severity', 'message', 'is_read', 'is_resolved', 
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['created_at', 'resolved_at']
    
    def validate(self, attrs):
        """Validações gerais do alerta."""
        if attrs.get('is_resolved') and not attrs.get('resolved_at'):
            attrs['resolved_at'] = timezone.now()
        return attrs


class ConsumptionSummarySerializer(serializers.Serializer):
    """Serializer para resumo de consumo."""
    
    total_consumption = serializers.FloatField()
    average_consumption = serializers.FloatField()
    peak_consumption = serializers.FloatField()
    consumption_by_device = serializers.DictField()
    consumption_by_hour = serializers.DictField()
    consumption_by_day = serializers.DictField()
    total_readings = serializers.IntegerField()
    active_alerts = serializers.IntegerField()


class ConsumptionStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas de consumo."""
    
    current_consumption = serializers.FloatField()
    daily_consumption = serializers.FloatField()
    weekly_consumption = serializers.FloatField()
    monthly_consumption = serializers.FloatField()
    consumption_trend = serializers.CharField()
    efficiency_score = serializers.FloatField()
    cost_estimate = serializers.FloatField()
