from rest_framework import serializers
from django.utils import timezone
from .models import ConsumptionReading, ConsumptionLimit, ConsumptionAlert, EnergyProduction, SolarPanel, EnergyManagementConfig
from devices.models import Device


class ConsumptionReadingSerializer(serializers.ModelSerializer):
    """Serializer para leituras de consumo."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    consumption_status = serializers.CharField(source='get_consumption_status', read_only=True)
    net_energy_balance = serializers.FloatField(source='get_net_energy_balance', read_only=True)
    energy_efficiency_status = serializers.CharField(source='get_energy_efficiency_status', read_only=True)
    
    class Meta:
        model = ConsumptionReading
        fields = [
            'id', 'device', 'device_name', 'device_id', 'timestamp', 
            'consumption_kwh', 'production_kwh', 'power_watts', 'voltage', 'current_amperage',
            'consumption_status', 'net_energy_balance', 'energy_efficiency_status', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def validate_consumption_kwh(self, value):
        """Valida o consumo em kWh."""
        if value < 0:
            raise serializers.ValidationError("Consumo não pode ser negativo.")
        return value
    
    def validate_production_kwh(self, value):
        """Valida a produção em kWh."""
        if value < 0:
            raise serializers.ValidationError("Produção não pode ser negativa.")
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
            'device', 'timestamp', 'consumption_kwh', 'production_kwh', 'power_watts', 
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


class EnergyProductionSerializer(serializers.ModelSerializer):
    """Serializer para leituras de produção de energia."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    production_efficiency = serializers.FloatField(source='get_production_efficiency', read_only=True)
    
    class Meta:
        model = EnergyProduction
        fields = [
            'id', 'device', 'device_name', 'device_id', 'timestamp', 
            'production_kwh', 'power_watts', 'solar_irradiance', 'temperature',
            'production_efficiency', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def validate_production_kwh(self, value):
        """Valida a produção em kWh."""
        if value < 0:
            raise serializers.ValidationError("Produção não pode ser negativa.")
        return value
    
    def validate_timestamp(self, value):
        """Valida o timestamp da leitura."""
        if value > timezone.now():
            raise serializers.ValidationError("Timestamp não pode ser no futuro.")
        return value


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


class EnergyBalanceSerializer(serializers.Serializer):
    """Serializer para comparação de energia em tempo real."""
    
    current_consumption = serializers.FloatField()
    current_production = serializers.FloatField()
    net_balance = serializers.FloatField()
    efficiency_status = serializers.CharField()
    daily_consumption = serializers.FloatField()
    daily_production = serializers.FloatField()
    daily_net_balance = serializers.FloatField()
    weekly_consumption = serializers.FloatField()
    weekly_production = serializers.FloatField()
    weekly_net_balance = serializers.FloatField()
    monthly_consumption = serializers.FloatField()
    monthly_production = serializers.FloatField()
    monthly_net_balance = serializers.FloatField()
    timestamp = serializers.DateTimeField()


class SolarPanelSerializer(serializers.ModelSerializer):
    """Serializer para inversores solares."""
    
    current_production = serializers.FloatField(source='get_current_production', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = SolarPanel
        fields = [
            'id', 'name', 'panel_id', 'nominal_power_kwp', 'is_active',
            'current_production', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def validate_nominal_power_kwp(self, value):
        """Valida a potência nominal."""
        if value <= 0:
            raise serializers.ValidationError("Potência nominal deve ser positiva.")
        return value
    
    def validate_panel_id(self, value):
        """Valida o ID do inversor."""
        if not value:
            raise serializers.ValidationError("ID do inversor é obrigatório.")
        return value


class SolarPanelCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de inversores solares."""
    
    class Meta:
        model = SolarPanel
        fields = ['name', 'panel_id', 'nominal_power_kwp', 'is_active']
    
    def create(self, validated_data):
        """Cria um novo inversor solar."""
        # Adicionar o usuário atual como criador
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SolarProductionSerializer(serializers.Serializer):
    """Serializer para dados de produção solar."""
    
    panel_id = serializers.CharField()
    panel_name = serializers.CharField()
    nominal_power_kwp = serializers.FloatField()
    current_production = serializers.FloatField()
    production_percentage = serializers.FloatField()
    is_active = serializers.BooleanField()


class SolarProductionSummarySerializer(serializers.Serializer):
    """Serializer para resumo de produção solar."""
    
    total_panels = serializers.IntegerField()
    active_panels = serializers.IntegerField()
    total_nominal_power = serializers.FloatField()
    total_current_production = serializers.FloatField()
    average_efficiency = serializers.FloatField()
    panels = SolarProductionSerializer(many=True)


class EnergyManagementConfigSerializer(serializers.ModelSerializer):
    """Serializer para configuração de gerenciamento de energia."""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = EnergyManagementConfig
        fields = [
            'id', 'name', 'deficit_threshold_percentage', 'auto_control_enabled',
            'is_active', 'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def validate_deficit_threshold_percentage(self, value):
        """Valida o percentual de limiar de déficit."""
        if not (0.0 <= value <= 500.0):
            raise serializers.ValidationError(
                "O percentual de limiar deve estar entre 0 e 500."
            )
        return value
    
    def create(self, validated_data):
        """Cria uma nova configuração."""
        # Se esta configuração será ativa, desativar as outras
        if validated_data.get('is_active', False):
            EnergyManagementConfig.objects.filter(is_active=True).update(is_active=False)
        
        # Adicionar o usuário atual como criador
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Atualiza uma configuração."""
        # Se esta configuração será ativa, desativar as outras
        if validated_data.get('is_active', False):
            EnergyManagementConfig.objects.filter(is_active=True).exclude(id=instance.id).update(is_active=False)
        
        return super().update(instance, validated_data)
