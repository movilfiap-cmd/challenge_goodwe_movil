from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
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
    production_kwh = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Produção (kWh)',
        help_text='Produção de energia em kWh no momento da leitura'
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
    
    def get_net_energy_balance(self):
        """Retorna o saldo energético (produção - consumo)."""
        return self.production_kwh - self.consumption_kwh
    
    def get_energy_efficiency_status(self):
        """Retorna o status de eficiência energética baseado no saldo."""
        net_balance = self.get_net_energy_balance()
        if net_balance > 0:
            return 'surplus'  # Excedente de energia
        elif net_balance < -self.device.max_consumption * 0.5:
            return 'deficit'  # Déficit significativo
        else:
            return 'balanced'  # Equilibrado


class EnergyProduction(models.Model):
    """Modelo para leituras de produção de energia."""
    
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='production_readings',
        verbose_name='Dispositivo',
        null=True,
        blank=True,
        help_text='Dispositivo associado (opcional para painéis solares)'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data e Hora',
        help_text='Data e hora da leitura'
    )
    production_kwh = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name='Produção (kWh)',
        help_text='Produção de energia em kWh no momento da leitura'
    )
    power_watts = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Potência (W)',
        help_text='Potência de produção em Watts no momento da leitura'
    )
    solar_irradiance = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Irradiância Solar (W/m²)',
        help_text='Irradiância solar em W/m²'
    )
    temperature = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Temperatura (°C)',
        help_text='Temperatura ambiente em Celsius'
    )
    
    # Campos de auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    
    class Meta:
        verbose_name = 'Leitura de Produção'
        verbose_name_plural = 'Leituras de Produção'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp.strftime('%d/%m/%Y %H:%M')} - {self.production_kwh:.2f} kWh"
    
    def get_production_efficiency(self):
        """Retorna a eficiência de produção baseada na irradiância solar."""
        if self.solar_irradiance and self.solar_irradiance > 0:
            # Eficiência aproximada baseada na irradiância solar
            expected_power = self.solar_irradiance * 0.2  # Assumindo 20% de eficiência
            if self.power_watts and expected_power > 0:
                return (self.power_watts / expected_power) * 100
        return None


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
        ('device_auto_controlled', 'Dispositivo Controlado Automaticamente'),
        ('medium_priority_action_needed', 'Ação Necessária - Prioridade Média'),
        ('deficit_detected', 'Déficit de Produção Detectado'),
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
        max_length=30,
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


class SolarPanel(models.Model):
    """Modelo para inversores solares."""
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome do Inversor',
        help_text='Nome amigável para o inversor solar'
    )
    panel_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='ID do Inversor',
        help_text='Identificador único do inversor solar'
    )
    nominal_power_kwp = models.FloatField(
        validators=[MinValueValidator(0.0)],
        verbose_name='Potência Nominal (kWp)',
        help_text='Potência nominal do inversor em kWp'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Se o inversor está ativo e sendo monitorado'
    )
    
    # Campos de auditoria
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_solar_panels',
        verbose_name='Criado por'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    class Meta:
        verbose_name = 'Inversor Solar'
        verbose_name_plural = 'Inversores Solares'
        ordering = ['name']
        indexes = [
            models.Index(fields=['panel_id']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.panel_id}) - {self.nominal_power_kwp} kWp"
    
    def get_current_production(self):
        """Calcula a produção atual baseada na hora do dia e condições meteorológicas."""
        from weather.models import WeatherForecast
        import random
        from datetime import datetime
        
        # Obter hora atual
        current_hour = datetime.now().hour
        
        # Calcular fator baseado na hora do dia
        if current_hour in [0, 1, 2, 3, 4, 5, 19, 20, 21, 22, 23]:  # Noite
            time_factor = 0.0
        elif current_hour in [6, 7, 8]:  # Manhã cedo
            time_factor = 0.2 + (current_hour - 6) * 0.1  # 0.2 a 0.4
        elif current_hour in [9, 10, 11]:  # Manhã
            time_factor = 0.5 + (current_hour - 9) * 0.2  # 0.5 a 0.9
        elif current_hour in [12, 13, 14]:  # Meio-dia (pico)
            time_factor = 0.9 + random.uniform(0, 0.1)  # 0.9 a 1.0
        elif current_hour in [15, 16, 17]:  # Tarde
            time_factor = 0.9 - (current_hour - 15) * 0.1  # 0.9 a 0.6
        elif current_hour == 18:  # Entardecer
            time_factor = 0.2 + random.uniform(0, 0.1)  # 0.2 a 0.3
        else:
            time_factor = 0.0
        
        # Obter fator meteorológico (usar São Paulo como padrão)
        try:
            weather_forecast = WeatherForecast.objects.filter(
                city__icontains='Sao Paulo',
                country='BR'
            ).order_by('-forecast_date').first()
            
            if weather_forecast:
                weather_factor = weather_forecast.get_solar_irradiance_factor()
            else:
                weather_factor = 0.8  # Padrão para céu parcialmente nublado
        except:
            weather_factor = 0.8
        
        # Calcular produção base
        base_production = self.nominal_power_kwp * time_factor * weather_factor
        
        # Adicionar variação aleatória (±5%)
        variance = random.uniform(-0.05, 0.05)
        final_production = base_production * (1 + variance)
        
        # Garantir que não seja negativo
        return max(0.0, final_production)


class EnergyManagementConfig(models.Model):
    """Modelo para configuração do gerenciamento automático de energia."""
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome da Configuração',
        help_text='Nome descritivo para a configuração'
    )
    deficit_threshold_percentage = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(500.0)],
        verbose_name='Limiar de Déficit (%)',
        help_text='Percentual mínimo de produção em relação ao consumo para evitar controle automático'
    )
    auto_control_enabled = models.BooleanField(
        default=True,
        verbose_name='Controle Automático Ativo',
        help_text='Se o controle automático de dispositivos está habilitado'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Configuração Ativa',
        help_text='Se esta é a configuração ativa (apenas uma pode estar ativa)'
    )
    
    # Campos de auditoria
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_energy_configs',
        verbose_name='Criado por'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    class Meta:
        verbose_name = 'Configuração de Gerenciamento de Energia'
        verbose_name_plural = 'Configurações de Gerenciamento de Energia'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['auto_control_enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.deficit_threshold_percentage}%"
    
    def save(self, *args, **kwargs):
        """Garante que apenas uma configuração esteja ativa."""
        if self.is_active:
            # Desativar todas as outras configurações
            EnergyManagementConfig.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Retorna a configuração ativa atual."""
        return cls.objects.filter(is_active=True).first()
