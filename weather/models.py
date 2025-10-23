from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class WeatherForecast(models.Model):
    """Modelo para previsões meteorológicas."""
    
    city = models.CharField(
        max_length=100,
        verbose_name='Cidade',
        help_text='Nome da cidade para a previsão'
    )
    country = models.CharField(
        max_length=10,
        verbose_name='País',
        help_text='Código do país (ex: BR, US)'
    )
    forecast_date = models.DateTimeField(
        verbose_name='Data da Previsão',
        help_text='Data e hora da previsão'
    )
    temperature = models.FloatField(
        verbose_name='Temperatura (°C)',
        help_text='Temperatura em Celsius'
    )
    humidity = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Umidade (%)',
        help_text='Umidade relativa do ar em porcentagem'
    )
    pressure = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name='Pressão (hPa)',
        help_text='Pressão atmosférica em hectopascais'
    )
    wind_speed = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name='Velocidade do Vento (m/s)',
        help_text='Velocidade do vento em metros por segundo'
    )
    wind_direction = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        verbose_name='Direção do Vento (°)',
        help_text='Direção do vento em graus'
    )
    cloudiness = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Nebulosidade (%)',
        help_text='Porcentagem de nebulosidade'
    )
    visibility = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Visibilidade (km)',
        help_text='Visibilidade em quilômetros'
    )
    uv_index = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(15)],
        verbose_name='Índice UV',
        help_text='Índice ultravioleta'
    )
    description = models.CharField(
        max_length=200,
        verbose_name='Descrição',
        help_text='Descrição das condições meteorológicas'
    )
    main_condition = models.CharField(
        max_length=50,
        verbose_name='Condição Principal',
        help_text='Condição meteorológica principal (ex: Clear, Clouds, Rain)'
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    class Meta:
        verbose_name = 'Previsão do Tempo'
        verbose_name_plural = 'Previsões do Tempo'
        ordering = ['-forecast_date']
        indexes = [
            models.Index(fields=['city', 'country', 'forecast_date']),
            models.Index(fields=['forecast_date']),
            models.Index(fields=['main_condition']),
        ]
        unique_together = ['city', 'country', 'forecast_date']
    
    def __str__(self):
        return f"{self.city}, {self.country} - {self.forecast_date.strftime('%d/%m/%Y %H:%M')}"
    
    def get_solar_irradiance_factor(self):
        """Calcula o fator de irradiação solar baseado nas condições meteorológicas."""
        # Fator baseado na condição principal
        condition_factors = {
            'Clear': 1.2,      # Céu limpo - alta irradiação
            'Clouds': 0.8,     # Nublado - irradiação reduzida
            'Rain': 0.6,       # Chuva - irradiação muito reduzida
            'Drizzle': 0.7,    # Garoa - irradiação reduzida
            'Thunderstorm': 0.5, # Tempestade - irradiação muito baixa
            'Snow': 0.4,       # Neve - irradiação muito baixa
            'Mist': 0.8,       # Névoa - irradiação reduzida
            'Fog': 0.7,        # Neblina - irradiação reduzida
        }
        
        base_factor = condition_factors.get(self.main_condition, 0.8)
        
        # Ajustar baseado na nebulosidade
        cloudiness_factor = 1 - (self.cloudiness / 100) * 0.3
        
        # Ajustar baseado na umidade (alta umidade reduz irradiação)
        humidity_factor = 1 - (self.humidity / 100) * 0.1
        
        # Calcular fator final
        final_factor = base_factor * cloudiness_factor * humidity_factor
        
        # Garantir que o fator esteja entre 0.3 e 1.2
        return max(0.3, min(1.2, final_factor))
    
    def get_energy_consumption_factor(self):
        """Calcula o fator de consumo de energia baseado nas condições meteorológicas."""
        # Fator baseado na temperatura (consumo de ar condicionado/aquecimento)
        temp_factor = 1.0
        if self.temperature > 30:  # Muito quente
            temp_factor = 1.3
        elif self.temperature > 25:  # Quente
            temp_factor = 1.1
        elif self.temperature < 10:  # Muito frio
            temp_factor = 1.2
        elif self.temperature < 15:  # Frio
            temp_factor = 1.05
        
        # Fator baseado na umidade (alta umidade aumenta consumo)
        humidity_factor = 1 + (self.humidity / 100) * 0.1
        
        # Fator baseado na condição meteorológica
        condition_factors = {
            'Clear': 1.0,      # Céu limpo - consumo normal
            'Clouds': 1.05,    # Nublado - ligeiro aumento
            'Rain': 1.1,       # Chuva - aumento no consumo
            'Drizzle': 1.05,   # Garoa - ligeiro aumento
            'Thunderstorm': 1.2, # Tempestade - aumento significativo
            'Snow': 1.3,       # Neve - aumento significativo
            'Mist': 1.05,      # Névoa - ligeiro aumento
            'Fog': 1.1,        # Neblina - aumento
        }
        
        condition_factor = condition_factors.get(self.main_condition, 1.0)
        
        # Calcular fator final
        final_factor = temp_factor * humidity_factor * condition_factor
        
        # Garantir que o fator esteja entre 0.8 e 1.5
        return max(0.8, min(1.5, final_factor))


class WeatherAlert(models.Model):
    """Modelo para alertas meteorológicos."""
    
    ALERT_TYPES = [
        ('temperature', 'Temperatura'),
        ('humidity', 'Umidade'),
        ('wind', 'Vento'),
        ('precipitation', 'Precipitação'),
        ('storm', 'Tempestade'),
        ('heat_wave', 'Onda de Calor'),
        ('cold_wave', 'Onda de Frio'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    city = models.CharField(
        max_length=100,
        verbose_name='Cidade'
    )
    country = models.CharField(
        max_length=10,
        verbose_name='País'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name='Tipo de Alerta'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        verbose_name='Severidade'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Título',
        help_text='Título do alerta'
    )
    description = models.TextField(
        verbose_name='Descrição',
        help_text='Descrição detalhada do alerta'
    )
    start_time = models.DateTimeField(
        verbose_name='Início',
        help_text='Data e hora de início do alerta'
    )
    end_time = models.DateTimeField(
        verbose_name='Fim',
        help_text='Data e hora de fim do alerta'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Se o alerta está ativo'
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    class Meta:
        verbose_name = 'Alerta Meteorológico'
        verbose_name_plural = 'Alertas Meteorológicos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['city', 'country']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['is_active', 'start_time', 'end_time']),
        ]
    
    def __str__(self):
        return f"{self.city} - {self.get_alert_type_display()} - {self.get_severity_display()}"
    
    def is_currently_active(self):
        """Verifica se o alerta está ativo no momento atual."""
        now = timezone.now()
        return (
            self.is_active and
            self.start_time <= now <= self.end_time
        )
