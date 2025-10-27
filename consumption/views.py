from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Max, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import ConsumptionReading, ConsumptionLimit, ConsumptionAlert, EnergyProduction, SolarPanel, EnergyManagementConfig
from .serializers import (
    ConsumptionReadingSerializer, ConsumptionReadingCreateSerializer,
    ConsumptionLimitSerializer, ConsumptionAlertSerializer,
    ConsumptionSummarySerializer, ConsumptionStatsSerializer,
    EnergyProductionSerializer, EnergyBalanceSerializer,
    SolarPanelSerializer, SolarPanelCreateSerializer,
    SolarProductionSummarySerializer, EnergyManagementConfigSerializer
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
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def energy_balance(self, request):
        """Retorna o balanço energético em tempo real."""
        queryset = self.get_queryset()
        
        # Consumo atual (última leitura)
        current_reading = queryset.first()
        current_consumption = current_reading.consumption_kwh if current_reading else 0.0
        current_production = current_reading.production_kwh if current_reading else 0.0
        net_balance = current_production - current_consumption
        
        # Determinar status de eficiência
        if net_balance > 0:
            efficiency_status = 'surplus'
        elif net_balance < -current_consumption * 0.5:
            efficiency_status = 'deficit'
        else:
            efficiency_status = 'balanced'
        
        # Consumo diário (hoje)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_stats = queryset.filter(
            timestamp__gte=today_start
        ).aggregate(
            consumption=Sum('consumption_kwh'),
            production=Sum('production_kwh')
        )
        daily_consumption = daily_stats['consumption'] or 0.0
        daily_production = daily_stats['production'] or 0.0
        daily_net_balance = daily_production - daily_consumption
        
        # Consumo semanal (últimos 7 dias)
        week_start = timezone.now() - timedelta(days=7)
        weekly_stats = queryset.filter(
            timestamp__gte=week_start
        ).aggregate(
            consumption=Sum('consumption_kwh'),
            production=Sum('production_kwh')
        )
        weekly_consumption = weekly_stats['consumption'] or 0.0
        weekly_production = weekly_stats['production'] or 0.0
        weekly_net_balance = weekly_production - weekly_consumption
        
        # Consumo mensal (últimos 30 dias)
        month_start = timezone.now() - timedelta(days=30)
        monthly_stats = queryset.filter(
            timestamp__gte=month_start
        ).aggregate(
            consumption=Sum('consumption_kwh'),
            production=Sum('production_kwh')
        )
        monthly_consumption = monthly_stats['consumption'] or 0.0
        monthly_production = monthly_stats['production'] or 0.0
        monthly_net_balance = monthly_production - monthly_consumption
        
        balance_data = {
            'current_consumption': current_consumption,
            'current_production': current_production,
            'net_balance': net_balance,
            'efficiency_status': efficiency_status,
            'daily_consumption': daily_consumption,
            'daily_production': daily_production,
            'daily_net_balance': daily_net_balance,
            'weekly_consumption': weekly_consumption,
            'weekly_production': weekly_production,
            'weekly_net_balance': weekly_net_balance,
            'monthly_consumption': monthly_consumption,
            'monthly_production': monthly_production,
            'monthly_net_balance': monthly_net_balance,
            'timestamp': timezone.now()
        }
        
        serializer = EnergyBalanceSerializer(balance_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_random_reading(self, request):
        """Gera leituras aleatórias de consumo e produção usando Celery."""
        from consumption.tasks import generate_complete_energy_reading
        
        # Run the task asynchronously
        task = generate_complete_energy_reading.delay()
        
        return Response({
            'message': 'Leituras sendo geradas em background',
            'task_id': task.id,
            'status': 'processing',
            'timestamp': timezone.now()
        })
    
    @action(detail=False, methods=['post'])
    def generate_random_reading_sync(self, request):
        """Gera leituras aleatórias de consumo e produção de forma síncrona."""
        from consumption.tasks import generate_complete_energy_reading
        
        # Run the task synchronously for immediate results
        result = generate_complete_energy_reading()
        
        if result['status'] == 'success':
            return Response({
                'message': 'Leituras geradas com sucesso',
                'timestamp': result['timestamp'],
                'total_consumption': result['consumption']['total_consumption'],
                'total_production': result['production']['total_production'],
                'net_balance': result['net_balance'],
                'devices_updated': result['consumption']['devices_updated'],
                'panels_updated': result['production']['panels_updated'],
                'alerts_created': result['consumption'].get('alerts_created', 0)
            })
        else:
            return Response({
                'message': result['message'],
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def energy_balance_history(self, request):
        """Retorna histórico do balanço energético para gráficos."""
        queryset = self.get_queryset()
        
        # Parâmetros opcionais
        days = int(request.query_params.get('days', 7))  # Padrão: últimos 7 dias
        days = min(days, 30)  # Limitar a 30 dias máximo
        
        # Calcular período
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Filtrar leituras do período
        period_readings = queryset.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        # Agrupar por dia
        daily_data = {}
        for reading in period_readings:
            date_key = reading.timestamp.date().strftime('%Y-%m-%d')
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'consumption': 0.0,
                    'production': 0.0,
                    'net_balance': 0.0
                }
            
            daily_data[date_key]['consumption'] += reading.consumption_kwh
            daily_data[date_key]['production'] += reading.production_kwh
            daily_data[date_key]['net_balance'] = daily_data[date_key]['production'] - daily_data[date_key]['consumption']
        
        # Preparar dados para o gráfico
        labels = []
        consumption_data = []
        production_data = []
        net_balance_data = []
        
        # Garantir que temos dados para todos os dias do período
        for i in range(days):
            current_date = (end_date.date() - timedelta(days=i))
            date_key = current_date.strftime('%Y-%m-%d')
            
            labels.insert(0, current_date.strftime('%d/%m'))
            
            if date_key in daily_data:
                consumption_data.insert(0, daily_data[date_key]['consumption'])
                production_data.insert(0, daily_data[date_key]['production'])
                net_balance_data.insert(0, daily_data[date_key]['net_balance'])
            else:
                # Se não há dados para este dia, usar 0
                consumption_data.insert(0, 0.0)
                production_data.insert(0, 0.0)
                net_balance_data.insert(0, 0.0)
        
        # Verificar se há dispositivos com dados
        devices_with_data = queryset.values_list('device__name', flat=True).distinct()
        
        history_data = {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Consumo (kWh)',
                    'data': consumption_data,
                    'borderColor': '#dc3545',
                    'backgroundColor': 'rgba(220, 53, 69, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Produção (kWh)',
                    'data': production_data,
                    'borderColor': '#28a745',
                    'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                    'fill': True
                }
            ],
            'devices_with_data': list(devices_with_data),
            'total_days': days,
            'has_data': len(devices_with_data) > 0
        }
        
        return Response(history_data)


class EnergyProductionViewSet(viewsets.ModelViewSet):
    """ViewSet para leituras de produção de energia."""
    
    queryset = EnergyProduction.objects.select_related('device')
    serializer_class = EnergyProductionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra leituras de produção baseado nos parâmetros da query."""
        queryset = EnergyProduction.objects.select_related('device')
        
        # Filtros opcionais
        device_id = self.request.query_params.get('device_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        min_production = self.request.query_params.get('min_production')
        max_production = self.request.query_params.get('max_production')
        
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
        
        if min_production:
            try:
                queryset = queryset.filter(production_kwh__gte=float(min_production))
            except ValueError:
                pass
        
        if max_production:
            try:
                queryset = queryset.filter(production_kwh__lte=float(max_production))
            except ValueError:
                pass
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['post'])
    def add_production_reading(self, request):
        """Adiciona uma nova leitura de produção."""
        serializer = EnergyProductionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class SolarPanelViewSet(viewsets.ModelViewSet):
    """ViewSet para inversores solares."""
    
    queryset = SolarPanel.objects.all()
    serializer_class = SolarPanelSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado baseado na ação."""
        if self.action in ['create', 'update', 'partial_update']:
            return SolarPanelCreateSerializer
        return SolarPanelSerializer
    
    def get_queryset(self):
        """Filtra inversores baseado nos parâmetros da query."""
        queryset = SolarPanel.objects.all()
        
        # Filtros opcionais
        is_active = self.request.query_params.get('is_active')
        created_by = self.request.query_params.get('created_by')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if created_by:
            queryset = queryset.filter(created_by__username=created_by)
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        """Define o usuário atual como criador do inversor."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current_production(self, request):
        """Retorna a produção atual de todos os inversores ativos."""
        active_panels = self.get_queryset().filter(is_active=True)
        
        panels_data = []
        total_nominal_power = 0
        total_current_production = 0
        
        for panel in active_panels:
            current_production = panel.get_current_production()
            production_percentage = (current_production / panel.nominal_power_kwp * 100) if panel.nominal_power_kwp > 0 else 0
            
            panels_data.append({
                'panel_id': panel.panel_id,
                'panel_name': panel.name,
                'nominal_power_kwp': panel.nominal_power_kwp,
                'current_production': current_production,
                'production_percentage': production_percentage,
                'is_active': panel.is_active
            })
            
            total_nominal_power += panel.nominal_power_kwp
            total_current_production += current_production
        
        average_efficiency = (total_current_production / total_nominal_power * 100) if total_nominal_power > 0 else 0
        
        summary_data = {
            'total_panels': active_panels.count(),
            'active_panels': active_panels.count(),
            'total_nominal_power': total_nominal_power,
            'total_current_production': total_current_production,
            'average_efficiency': average_efficiency,
            'panels': panels_data
        }
        
        serializer = SolarProductionSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def production_history(self, request, pk=None):
        """Retorna histórico de produção de um inversor específico."""
        panel = self.get_object()
        
        # Por enquanto, retornar dados simulados
        # Em uma implementação real, isso viria de leituras históricas
        history_data = {
            'panel_id': panel.panel_id,
            'panel_name': panel.name,
            'current_production': panel.get_current_production(),
            'nominal_power_kwp': panel.nominal_power_kwp,
            'message': 'Histórico de produção será implementado em versão futura'
        }
        
        return Response(history_data)


class EnergyManagementConfigViewSet(viewsets.ModelViewSet):
    """ViewSet para configuração de gerenciamento de energia."""
    
    queryset = EnergyManagementConfig.objects.all()
    serializer_class = EnergyManagementConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra configurações baseado nos parâmetros da query."""
        queryset = EnergyManagementConfig.objects.all()
        
        # Filtros opcionais
        is_active = self.request.query_params.get('is_active')
        auto_control_enabled = self.request.query_params.get('auto_control_enabled')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if auto_control_enabled is not None:
            queryset = queryset.filter(auto_control_enabled=auto_control_enabled.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Define o usuário atual como criador da configuração."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Retorna a configuração ativa atual."""
        active_config = EnergyManagementConfig.get_active_config()
        
        if active_config:
            serializer = self.get_serializer(active_config)
            return Response(serializer.data)
        else:
            return Response({
                'message': 'Nenhuma configuração ativa encontrada',
                'deficit_threshold_percentage': 100.0,
                'auto_control_enabled': True
            })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Ativa uma configuração específica."""
        config = self.get_object()
        
        # Desativar todas as outras configurações
        EnergyManagementConfig.objects.filter(is_active=True).update(is_active=False)
        
        # Ativar esta configuração
        config.is_active = True
        config.save()
        
        return Response({
            'message': 'Configuração ativada com sucesso.',
            'config': self.get_serializer(config).data
        })
    
    @action(detail=False, methods=['post'])
    def toggle_auto_control(self, request):
        """Ativa/desativa o controle automático na configuração ativa."""
        active_config = EnergyManagementConfig.get_active_config()
        
        if not active_config:
            return Response(
                {'error': 'Nenhuma configuração ativa encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        auto_control_enabled = request.data.get('auto_control_enabled')
        
        if auto_control_enabled is None:
            return Response(
                {'error': 'Campo "auto_control_enabled" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            auto_control_enabled = bool(auto_control_enabled)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Valor inválido para auto_control_enabled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        active_config.auto_control_enabled = auto_control_enabled
        active_config.save()
        
        return Response({
            'message': f'Controle automático {"ativado" if auto_control_enabled else "desativado"} com sucesso.',
            'auto_control_enabled': active_config.auto_control_enabled
        })
