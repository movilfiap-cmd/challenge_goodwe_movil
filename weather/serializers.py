from rest_framework import serializers
from .models import WeatherForecast, WeatherAlert


class WeatherForecastSerializer(serializers.ModelSerializer):
    """Serializer para previsões meteorológicas."""
    
    solar_irradiance_factor = serializers.FloatField(source='get_solar_irradiance_factor', read_only=True)
    energy_consumption_factor = serializers.FloatField(source='get_energy_consumption_factor', read_only=True)
    
    class Meta:
        model = WeatherForecast
        fields = [
            'id', 'city', 'country', 'forecast_date', 'temperature', 
            'humidity', 'pressure', 'wind_speed', 'wind_direction',
            'cloudiness', 'visibility', 'uv_index', 'description',
            'main_condition', 'solar_irradiance_factor', 'energy_consumption_factor',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_temperature(self, value):
        """Valida a temperatura."""
        if value < -50 or value > 60:
            raise serializers.ValidationError("Temperatura deve estar entre -50°C e 60°C.")
        return value
    
    def validate_humidity(self, value):
        """Valida a umidade."""
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Umidade deve estar entre 0% e 100%.")
        return value
    
    def validate_wind_direction(self, value):
        """Valida a direção do vento."""
        if not (0 <= value <= 360):
            raise serializers.ValidationError("Direção do vento deve estar entre 0° e 360°.")
        return value


class WeatherAlertSerializer(serializers.ModelSerializer):
    """Serializer para alertas meteorológicos."""
    
    is_currently_active = serializers.BooleanField(source='is_currently_active', read_only=True)
    
    class Meta:
        model = WeatherAlert
        fields = [
            'id', 'city', 'country', 'alert_type', 'severity', 'title',
            'description', 'start_time', 'end_time', 'is_active',
            'is_currently_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validações gerais do alerta."""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                "A data de início deve ser anterior à data de fim."
            )
        
        return attrs


class WeatherSummarySerializer(serializers.Serializer):
    """Serializer para resumo meteorológico."""
    
    current_temperature = serializers.FloatField()
    current_humidity = serializers.IntegerField()
    current_condition = serializers.CharField()
    solar_irradiance_factor = serializers.FloatField()
    energy_consumption_factor = serializers.FloatField()
    active_alerts = serializers.IntegerField()
    forecast_24h = serializers.ListField()
    forecast_7d = serializers.ListField()


class WeatherStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas meteorológicas."""
    
    average_temperature = serializers.FloatField()
    max_temperature = serializers.FloatField()
    min_temperature = serializers.FloatField()
    average_humidity = serializers.FloatField()
    average_wind_speed = serializers.FloatField()
    most_common_condition = serializers.CharField()
    clear_days = serializers.IntegerField()
    rainy_days = serializers.IntegerField()
    cloudy_days = serializers.IntegerField()
