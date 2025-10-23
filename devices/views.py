from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q, F
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Device, DeviceStatus
from .serializers import (
    DeviceSerializer, DeviceCreateSerializer, DeviceStatusSerializer,
    DeviceListSerializer, DeviceSummarySerializer
)


class DeviceViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de dispositivos."""
    
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado baseado na ação."""
        if self.action == 'create':
            return DeviceCreateSerializer
        elif self.action == 'list':
            return DeviceListSerializer
        return DeviceSerializer
    
    def get_queryset(self):
        """Filtra dispositivos baseado nos parâmetros da query."""
        queryset = Device.objects.select_related('created_by').prefetch_related('status')
        
        # Filtros opcionais
        device_type = self.request.query_params.get('device_type')
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')
        
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(device_id__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Define o usuário criador do dispositivo."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Ativa/desativa um dispositivo."""
        device = self.get_object()
        device.is_active = not device.is_active
        device.save()
        
        return Response({
            'message': f'Dispositivo {"ativado" if device.is_active else "desativado"} com sucesso.',
            'is_active': device.is_active
        })
    
    @action(detail=True, methods=['post'])
    def update_consumption(self, request, pk=None):
        """Atualiza o consumo de um dispositivo."""
        device = self.get_object()
        consumption = request.data.get('consumption')
        
        if consumption is None:
            return Response(
                {'error': 'Campo "consumption" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            consumption = float(consumption)
            if consumption < 0:
                raise ValueError("Consumo não pode ser negativo.")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Consumo deve ser um número positivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        device.last_consumption = consumption
        device.save()
        
        return Response({
            'message': 'Consumo atualizado com sucesso.',
            'consumption': device.last_consumption,
            'status': device.get_consumption_status()
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retorna um resumo dos dispositivos."""
        queryset = self.get_queryset()
        
        # Estatísticas básicas
        total_devices = queryset.count()
        active_devices = queryset.filter(is_active=True).count()
        
        # Consumo total e médio
        consumption_data = queryset.aggregate(
            total=Sum('last_consumption'),
            average=Avg('last_consumption')
        )
        total_consumption = consumption_data['total'] or 0.0
        average_consumption = consumption_data['average'] or 0.0
        
        # Dispositivos por tipo
        devices_by_type = dict(
            queryset.values('device_type').annotate(count=Count('id')).values_list('device_type', 'count')
        )
        
        # Consumo por tipo
        consumption_by_type = {}
        for device_type, _ in Device.DeviceType.choices:
            consumption = queryset.filter(device_type=device_type).aggregate(
                total=Sum('last_consumption')
            )['total'] or 0.0
            consumption_by_type[device_type] = consumption
        
        summary_data = {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'total_consumption': total_consumption,
            'average_consumption': average_consumption,
            'devices_by_type': devices_by_type,
            'consumption_by_type': consumption_by_type
        }
        
        serializer = DeviceSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def status_overview(self, request):
        """Retorna uma visão geral do status dos dispositivos."""
        devices = self.get_queryset()
        
        # Status de consumo
        consumption_status = {
            'normal': devices.filter(last_consumption__lte=F('max_consumption') * 0.8).count(),
            'caution': devices.filter(
                last_consumption__gt=F('max_consumption') * 0.8,
                last_consumption__lte=F('max_consumption')
            ).count(),
            'warning': devices.filter(last_consumption__gt=F('max_consumption')).count()
        }
        
        # Status online (se disponível)
        online_status = {
            'online': 0,
            'offline': 0
        }
        
        for device in devices:
            try:
                status = device.status
                if status.is_online:
                    online_status['online'] += 1
                else:
                    online_status['offline'] += 1
            except DeviceStatus.DoesNotExist:
                online_status['offline'] += 1
        
        return Response({
            'consumption_status': consumption_status,
            'online_status': online_status,
            'last_updated': timezone.now()
        })


class DeviceStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consulta de status dos dispositivos."""
    
    queryset = DeviceStatus.objects.select_related('device')
    serializer_class = DeviceStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra status baseado nos parâmetros da query."""
        queryset = DeviceStatus.objects.select_related('device')
        
        # Filtros opcionais
        is_online = self.request.query_params.get('is_online')
        device_id = self.request.query_params.get('device_id')
        
        if is_online is not None:
            queryset = queryset.filter(is_online=is_online.lower() == 'true')
        
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Atualiza o status de um dispositivo."""
        device_status = self.get_object()
        
        is_online = request.data.get('is_online', device_status.is_online)
        current_power = request.data.get('current_power', device_status.current_power)
        voltage = request.data.get('voltage', device_status.voltage)
        current_amperage = request.data.get('current_amperage', device_status.current_amperage)
        
        # Atualizar campos
        device_status.is_online = is_online
        device_status.current_power = current_power
        device_status.voltage = voltage
        device_status.current_amperage = current_amperage
        
        if is_online:
            device_status.last_seen = timezone.now()
        
        device_status.save()
        
        return Response({
            'message': 'Status atualizado com sucesso.',
            'status': DeviceStatusSerializer(device_status).data
        })
