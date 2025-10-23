from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from devices.models import Device


class ConsumptionReading(models.Model):
    """Modelo para leituras de consumo de energia."""
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='consumption_readings',
        verbose_name='Dispositivo'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data e Hora',
        help_text='Data e hora da leitura'
    )
    consumption_kwh = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name='Consumo (kWh)',
        help_text='Consumo em kWh no momento da leitura'
    )
    power_watts = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Potência (W)',
        help_text='Potência em Watts no momento da leitura'
    )
    voltage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Voltagem (V)',
        help_text='Voltagem em Volts no momento da leitura'
    )
    current_amperage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Corrente (A)',
        help_text='Corrente em Amperes no momento da leitura'
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    
    class Meta:
        verbose_name = 'Leitura de Consumo'
        verbose_name_plural = 'Leituras de Consumo'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp.strftime('%d/%m/%Y %H:%M')} - {self.consumption_kwh:.2f} kWh"
    
    def get_consumption_status(self):
        """Retorna o status do consumo baseado no limite do dispositivo."""
        if self.consumption_kwh > self.device.max_consumption:
            return 'warning'
        elif self.consumption_kwh > self.device.max_consumption * 0.8:
            return 'caution'
        return 'normal'


class ConsumptionLimit(models.Model):
    """Modelo para limites de consumo configuráveis."""
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome do Limite',
        help_text='Nome descritivo para o limite'
    )
    base_limit_kwh = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name='Limite Base (kWh)',
        help_text='Limite base de consumo em kWh'
    )
    weather_factor = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1)],
        verbose_name='Fator Meteorológico',
        help_text='Fator aplicado baseado na previsão do tempo'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Se o limite está ativo'
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
        verbose_name = 'Limite de Consumo'
        verbose_name_plural = 'Limites de Consumo'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.get_effective_limit():.2f} kWh"
    
    def get_effective_limit(self):
        """Retorna o limite efetivo considerando o fator meteorológico."""
        return self.base_limit_kwh * self.weather_factor


class ConsumptionAlert(models.Model):
    """Modelo para alertas de consumo."""
    
    ALERT_TYPES = [
        ('high_consumption', 'Consumo Alto'),
        ('limit_exceeded', 'Limite Excedido'),
        ('device_offline', 'Dispositivo Offline'),
        ('unusual_pattern', 'Padrão Incomum'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='Dispositivo'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name='Tipo de Alerta'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium',
        verbose_name='Severidade'
    )
    message = models.TextField(
        verbose_name='Mensagem',
        help_text='Mensagem descritiva do alerta'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Lido',
        help_text='Se o alerta foi lido'
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name='Resolvido',
        help_text='Se o alerta foi resolvido'
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Resolução'
    )
    
    class Meta:
        verbose_name = 'Alerta de Consumo'
        verbose_name_plural = 'Alertas de Consumo'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device', 'alert_type']),
            models.Index(fields=['is_read', 'is_resolved']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.get_alert_type_display()} - {self.get_severity_display()}"
    
    def mark_as_read(self):
        """Marca o alerta como lido."""
        self.is_read = True
        self.save()
    
    def mark_as_resolved(self):
        """Marca o alerta como resolvido."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()
