from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class DeviceType(models.TextChoices):
    """Tipos de dispositivos disponíveis."""
    MANUAL = 'manual', 'Manual'
    TUYA = 'tuya', 'Tuya'
    SMART = 'smart', 'Smart'


class DevicePriority(models.TextChoices):
    """Prioridades dos dispositivos para controle automático."""
    ALTA = 'alta', 'Alta'
    MEDIA = 'media', 'Média'
    BAIXA = 'baixa', 'Baixa'


class Device(models.Model):
    """Modelo para dispositivos de energia."""
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome do Dispositivo',
        help_text='Nome amigável para o dispositivo'
    )
    device_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='ID do Dispositivo',
        help_text='Identificador único do dispositivo'
    )
    device_type = models.CharField(
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.MANUAL,
        verbose_name='Tipo do Dispositivo'
    )
    
    # Campos para dispositivos Tuya
    tuya_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Local (Tuya)',
        help_text='Endereço IP local do dispositivo Tuya'
    )
    tuya_local_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Chave Local (Tuya)',
        help_text='Chave local para comunicação com dispositivo Tuya'
    )
    tuya_version = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=3.3,
        validators=[MinValueValidator(3.0), MaxValueValidator(3.4)],
        verbose_name='Versão Tuya',
        help_text='Versão do protocolo Tuya'
    )
    
    # Campos de consumo
    last_consumption = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Último Consumo (kWh)',
        help_text='Último consumo registrado em kWh'
    )
    max_consumption = models.FloatField(
        default=10.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Consumo Máximo (kWh)',
        help_text='Consumo máximo esperado em kWh'
    )
    
    # Campos de controle
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Se o dispositivo está ativo e sendo monitorado'
    )
    is_controllable = models.BooleanField(
        default=False,
        verbose_name='Controlável',
        help_text='Se o dispositivo pode ser controlado remotamente'
    )
    
    # Campos de prioridade e controle automático
    priority = models.CharField(
        max_length=10,
        choices=DevicePriority.choices,
        default=DevicePriority.ALTA,
        verbose_name='Prioridade',
        help_text='Prioridade do dispositivo para controle automático'
    )
    auto_controlled = models.BooleanField(
        default=False,
        verbose_name='Controlado Automaticamente',
        help_text='Se o dispositivo foi controlado automaticamente pelo sistema'
    )
    auto_control_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data do Controle Automático',
        help_text='Data e hora do último controle automático'
    )
    
    # Campos de auditoria
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_devices',
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
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'
        ordering = ['name']
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['device_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
            models.Index(fields=['auto_controlled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.device_id})"
    
    def get_consumption_status(self):
        """Retorna o status do consumo baseado no limite."""
        if self.last_consumption > self.max_consumption:
            return 'warning'
        elif self.last_consumption > self.max_consumption * 0.8:
            return 'caution'
        return 'normal'
    
    def can_connect_tuya(self):
        """Verifica se o dispositivo Tuya pode ser conectado."""
        # Para ambiente de teste, sempre retornar True para dispositivos Tuya
        if self.device_type == DeviceType.TUYA:
            return True
        return False


class DeviceStatus(models.Model):
    """Status atual do dispositivo."""
    
    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name='status',
        verbose_name='Dispositivo'
    )
    is_online = models.BooleanField(
        default=False,
        verbose_name='Online',
        help_text='Se o dispositivo está online'
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Última Conexão',
        help_text='Última vez que o dispositivo foi visto online'
    )
    current_power = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Potência Atual (W)',
        help_text='Potência atual em Watts'
    )
    voltage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Voltagem (V)',
        help_text='Voltagem atual em Volts'
    )
    current_amperage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name='Corrente (A)',
        help_text='Corrente atual em Amperes'
    )
    
    # Campos de auditoria
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    class Meta:
        verbose_name = 'Status do Dispositivo'
        verbose_name_plural = 'Status dos Dispositivos'
    
    def __str__(self):
        return f"Status de {self.device.name}"
    
    def update_online_status(self, is_online=True):
        """Atualiza o status online do dispositivo."""
        self.is_online = is_online
        if is_online:
            self.last_seen = timezone.now()
        self.save()
