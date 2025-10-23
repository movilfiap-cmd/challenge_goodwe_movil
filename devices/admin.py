from django.contrib import admin
from django.utils.html import format_html
from .models import Device, DeviceStatus


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'device_id', 'device_type', 'last_consumption', 
        'max_consumption', 'is_active', 'consumption_status', 'created_at'
    ]
    list_filter = ['device_type', 'is_active', 'is_controllable', 'created_at']
    search_fields = ['name', 'device_id', 'tuya_ip']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'device_id', 'device_type', 'created_by')
        }),
        ('Configurações Tuya', {
            'fields': ('tuya_ip', 'tuya_local_key', 'tuya_version'),
            'classes': ('collapse',)
        }),
        ('Consumo', {
            'fields': ('last_consumption', 'max_consumption')
        }),
        ('Controle', {
            'fields': ('is_active', 'is_controllable')
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def consumption_status(self, obj):
        """Exibe o status do consumo com cores."""
        status = obj.get_consumption_status()
        if status == 'warning':
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Alto</span>'
            )
        elif status == 'caution':
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ Médio</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">✅ Normal</span>'
        )
    consumption_status.short_description = 'Status do Consumo'


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = [
        'device', 'is_online', 'last_seen', 'current_power', 
        'voltage', 'current_amperage', 'updated_at'
    ]
    list_filter = ['is_online', 'updated_at']
    search_fields = ['device__name', 'device__device_id']
    readonly_fields = ['updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device')
