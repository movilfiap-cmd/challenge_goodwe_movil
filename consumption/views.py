from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Max, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import ConsumptionReading, ConsumptionLimit, ConsumptionAlert
from .serializers import (
    ConsumptionReadingSerializer, ConsumptionReadingCreateSerializer,
    ConsumptionLimitSerializer, ConsumptionAlertSerializer,
    ConsumptionSummarySerializer, ConsumptionStatsSerializer
)


class ConsumptionReadingViewSet(viewsets.ModelViewSet):
    """ViewSet para leituras de consumo."""
    
    queryset = ConsumptionReading.objects.select_related('device')
    serializer_class = ConsumptionReadingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado baseado na ação."""
        if self.action == 'create':
            return ConsumptionReadingCreateSerializer
        return ConsumptionReadingSerializer
    
    def get_queryset(self):
        """Filtra leituras baseado nos parâmetros da query."""
        queryset = ConsumptionReading.objects.select_related('device')
        
        # Filtros opcionais
        device_id = self.request.query_params.get('device_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        min_consumption = self.request.query_params.get('min_consumption')
        max_consumption = self.request.query_params.get('max_consumption')
        
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_date)
            except ValueError:
                pass
        
        if min_consumption:
            try:
                queryset = queryset.filter(consumption_kwh__gte=float(min_consumption))
            except ValueError:
                pass
        
        if max_consumption:
            try:
                queryset = queryset.filter(consumption_kwh__lte=float(max_consumption))
            except ValueError:
                pass
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retorna um resumo das leituras de consumo."""
        queryset = self.get_queryset()
        
        # Período padrão: últimos 30 dias
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Aplicar filtros de data se fornecidos
        if 'start_date' in request.query_params:
            try:
                start_date = datetime.fromisoformat(
                    request.query_params['start_date'].replace('Z', '+00:00')
                )
            except ValueError:
                pass
        
        if 'end_date' in request.query_params:
            try:
                end_date = datetime.fromisoformat(
                    request.query_params['end_date'].replace('Z', '+00:00')
                )
            except ValueError:
                pass
        
        # Filtrar por período
        period_queryset = queryset.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        # Estatísticas básicas
        total_consumption = period_queryset.aggregate(
            total=Sum('consumption_kwh')
        )['total'] or 0.0
        
        average_consumption = period_queryset.aggregate(
            average=Avg('consumption_kwh')
        )['average'] or 0.0
        
        peak_consumption = period_queryset.aggregate(
            peak=Max('consumption_kwh')
        )['peak'] or 0.0
        
        # Consumo por dispositivo
        consumption_by_device = dict(
            period_queryset.values('device__name').annotate(
                total=Sum('consumption_kwh')
            ).values_list('device__name', 'total')
        )
        
        # Consumo por hora (últimas 24 horas)
        hourly_consumption = {}
        for hour in range(24):
            hour_start = end_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_consumption = period_queryset.filter(
                timestamp__gte=hour_start,
                timestamp__lt=hour_end
            ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
            
            hourly_consumption[f"{hour:02d}:00"] = hour_consumption
        
        # Consumo por dia (últimos 7 dias)
        daily_consumption = {}
        for day in range(7):
            day_date = end_date.date() - timedelta(days=day)
            day_start = timezone.make_aware(datetime.combine(day_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            day_consumption = period_queryset.filter(
                timestamp__gte=day_start,
                timestamp__lt=day_end
            ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
            
            daily_consumption[day_date.strftime('%Y-%m-%d')] = day_consumption
        
        # Total de leituras
        total_readings = period_queryset.count()
        
        # Alertas ativos
        active_alerts = ConsumptionAlert.objects.filter(
            is_resolved=False
        ).count()
        
        summary_data = {
            'total_consumption': total_consumption,
            'average_consumption': average_consumption,
            'peak_consumption': peak_consumption,
            'consumption_by_device': consumption_by_device,
            'consumption_by_hour': hourly_consumption,
            'consumption_by_day': daily_consumption,
            'total_readings': total_readings,
            'active_alerts': active_alerts
        }
        
        serializer = ConsumptionSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Retorna estatísticas detalhadas de consumo."""
        queryset = self.get_queryset()
        
        # Consumo atual (última leitura)
        current_reading = queryset.first()
        current_consumption = current_reading.consumption_kwh if current_reading else 0.0
        
        # Consumo diário (hoje)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_consumption = queryset.filter(
            timestamp__gte=today_start
        ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
        
        # Consumo semanal (últimos 7 dias)
        week_start = timezone.now() - timedelta(days=7)
        weekly_consumption = queryset.filter(
            timestamp__gte=week_start
        ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
        
        # Consumo mensal (últimos 30 dias)
        month_start = timezone.now() - timedelta(days=30)
        monthly_consumption = queryset.filter(
            timestamp__gte=month_start
        ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
        
        # Tendência de consumo (comparar últimas 2 semanas)
        two_weeks_ago = timezone.now() - timedelta(days=14)
        week_1_consumption = queryset.filter(
            timestamp__gte=two_weeks_ago,
            timestamp__lt=week_start
        ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
        
        week_2_consumption = queryset.filter(
            timestamp__gte=week_start
        ).aggregate(total=Sum('consumption_kwh'))['total'] or 0.0
        
        if week_1_consumption > 0:
            trend_percentage = ((week_2_consumption - week_1_consumption) / week_1_consumption) * 100
            if trend_percentage > 5:
                consumption_trend = 'increasing'
            elif trend_percentage < -5:
                consumption_trend = 'decreasing'
            else:
                consumption_trend = 'stable'
        else:
            consumption_trend = 'stable'
        
        # Score de eficiência (baseado na consistência do consumo)
        efficiency_score = 100.0  # Implementar lógica mais sofisticada
        
        # Estimativa de custo (assumindo R$ 0.50 por kWh)
        cost_per_kwh = 0.50
        cost_estimate = monthly_consumption * cost_per_kwh
        
        stats_data = {
            'current_consumption': current_consumption,
            'daily_consumption': daily_consumption,
            'weekly_consumption': weekly_consumption,
            'monthly_consumption': monthly_consumption,
            'consumption_trend': consumption_trend,
            'efficiency_score': efficiency_score,
            'cost_estimate': cost_estimate
        }
        
        serializer = ConsumptionStatsSerializer(stats_data)
        return Response(serializer.data)


class ConsumptionLimitViewSet(viewsets.ModelViewSet):
    """ViewSet para limites de consumo."""
    
    queryset = ConsumptionLimit.objects.all()
    serializer_class = ConsumptionLimitSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def update_weather_factor(self, request, pk=None):
        """Atualiza o fator meteorológico de um limite."""
        limit = self.get_object()
        weather_factor = request.data.get('weather_factor')
        
        if weather_factor is None:
            return Response(
                {'error': 'Campo "weather_factor" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weather_factor = float(weather_factor)
            if weather_factor <= 0:
                raise ValueError("Fator meteorológico deve ser positivo.")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Fator meteorológico deve ser um número positivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        limit.weather_factor = weather_factor
        limit.save()
        
        return Response({
            'message': 'Fator meteorológico atualizado com sucesso.',
            'weather_factor': limit.weather_factor,
            'effective_limit': limit.get_effective_limit()
        })


class ConsumptionAlertViewSet(viewsets.ModelViewSet):
    """ViewSet para alertas de consumo."""
    
    queryset = ConsumptionAlert.objects.select_related('device')
    serializer_class = ConsumptionAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra alertas baseado nos parâmetros da query."""
        queryset = ConsumptionAlert.objects.select_related('device')
        
        # Filtros opcionais
        is_read = self.request.query_params.get('is_read')
        is_resolved = self.request.query_params.get('is_resolved')
        alert_type = self.request.query_params.get('alert_type')
        severity = self.request.query_params.get('severity')
        device_id = self.request.query_params.get('device_id')
        
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marca um alerta como lido."""
        alert = self.get_object()
        alert.mark_as_read()
        
        return Response({
            'message': 'Alerta marcado como lido.',
            'is_read': alert.is_read
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_resolved(self, request, pk=None):
        """Marca um alerta como resolvido."""
        alert = self.get_object()
        alert.mark_as_resolved()
        
        return Response({
            'message': 'Alerta marcado como resolvido.',
            'is_resolved': alert.is_resolved,
            'resolved_at': alert.resolved_at
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Retorna o número de alertas não lidos."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
