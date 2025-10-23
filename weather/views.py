from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Count
from django.utils import timezone
from datetime import timedelta
import requests
from django.conf import settings
from .models import WeatherForecast, WeatherAlert
from .serializers import (
    WeatherForecastSerializer, WeatherAlertSerializer,
    WeatherSummarySerializer, WeatherStatsSerializer
)


class WeatherForecastViewSet(viewsets.ModelViewSet):
    """ViewSet para previsões meteorológicas."""
    
    queryset = WeatherForecast.objects.all()
    serializer_class = WeatherForecastSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra previsões baseado nos parâmetros da query."""
        queryset = WeatherForecast.objects.all()
        
        # Filtros opcionais
        city = self.request.query_params.get('city')
        country = self.request.query_params.get('country')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        main_condition = self.request.query_params.get('main_condition')
        
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        if country:
            queryset = queryset.filter(country__iexact=country)
        
        if start_date:
            try:
                start_date = timezone.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(forecast_date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = timezone.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(forecast_date__lte=end_date)
            except ValueError:
                pass
        
        if main_condition:
            queryset = queryset.filter(main_condition__iexact=main_condition)
        
        return queryset.order_by('-forecast_date')
    
    @action(detail=False, methods=['post'])
    def fetch_forecast(self, request):
        """Busca previsão do tempo da API OpenWeather."""
        city = request.data.get('city', 'Sao Paulo')
        country = request.data.get('country', 'BR')
        
        api_key = settings.OPENWEATHER_API_KEY
        if not api_key:
            return Response(
                {'error': 'Chave da API OpenWeather não configurada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # URL da API OpenWeather
        url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city},{country}&appid={api_key}&lang=pt_br&units=metric"
        )
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if response.status_code != 200:
                return Response(
                    {'error': f"Erro na API: {data.get('message', 'Erro desconhecido')}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Processar dados da API
            forecasts = data.get('list', [])
            created_forecasts = []
            
            for item in forecasts:
                # Extrair dados da previsão
                forecast_date = timezone.datetime.fromtimestamp(
                    item['dt'], tz=timezone.get_current_timezone()
                )
                
                weather = item['weather'][0]
                main = item['main']
                wind = item.get('wind', {})
                clouds = item.get('clouds', {})
                visibility = item.get('visibility', 0) / 1000  # Converter para km
                
                # Criar ou atualizar previsão
                forecast, created = WeatherForecast.objects.update_or_create(
                    city=city,
                    country=country,
                    forecast_date=forecast_date,
                    defaults={
                        'temperature': main['temp'],
                        'humidity': main['humidity'],
                        'pressure': main['pressure'],
                        'wind_speed': wind.get('speed', 0),
                        'wind_direction': wind.get('deg', 0),
                        'cloudiness': clouds.get('all', 0),
                        'visibility': visibility,
                        'uv_index': None,  # Não disponível na API gratuita
                        'description': weather['description'],
                        'main_condition': weather['main'],
                    }
                )
                
                created_forecasts.append(forecast)
            
            return Response({
                'message': f'Previsões atualizadas para {city}, {country}',
                'forecasts_created': len(created_forecasts),
                'forecasts': WeatherForecastSerializer(created_forecasts, many=True).data
            })
            
        except requests.RequestException as e:
            return Response(
                {'error': f'Erro ao conectar com a API: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Erro interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retorna um resumo das condições meteorológicas."""
        city = request.query_params.get('city', 'Sao Paulo')
        country = request.query_params.get('country', 'BR')
        
        # Previsão atual (mais recente)
        current_forecast = WeatherForecast.objects.filter(
            city__icontains=city,
            country__iexact=country
        ).order_by('-forecast_date').first()
        
        if not current_forecast:
            return Response(
                {'error': 'Nenhuma previsão encontrada para a cidade especificada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Previsões das próximas 24 horas
        next_24h = WeatherForecast.objects.filter(
            city__icontains=city,
            country__iexact=country,
            forecast_date__gte=timezone.now(),
            forecast_date__lte=timezone.now() + timedelta(hours=24)
        ).order_by('forecast_date')[:8]
        
        # Previsões dos próximos 7 dias (uma por dia)
        next_7d = WeatherForecast.objects.filter(
            city__icontains=city,
            country__iexact=country,
            forecast_date__gte=timezone.now(),
            forecast_date__lte=timezone.now() + timedelta(days=7)
        ).order_by('forecast_date')
        
        # Alertas ativos
        active_alerts = WeatherAlert.objects.filter(
            city__icontains=city,
            country__iexact=country,
            is_active=True,
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).count()
        
        summary_data = {
            'current_temperature': current_forecast.temperature,
            'current_humidity': current_forecast.humidity,
            'current_condition': current_forecast.main_condition,
            'solar_irradiance_factor': current_forecast.get_solar_irradiance_factor(),
            'energy_consumption_factor': current_forecast.get_energy_consumption_factor(),
            'active_alerts': active_alerts,
            'forecast_24h': WeatherForecastSerializer(next_24h, many=True).data,
            'forecast_7d': WeatherForecastSerializer(next_7d, many=True).data
        }
        
        serializer = WeatherSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Retorna estatísticas meteorológicas."""
        city = request.query_params.get('city', 'Sao Paulo')
        country = request.query_params.get('country', 'BR')
        
        # Período: últimos 30 dias
        start_date = timezone.now() - timedelta(days=30)
        
        queryset = WeatherForecast.objects.filter(
            city__icontains=city,
            country__iexact=country,
            forecast_date__gte=start_date
        )
        
        if not queryset.exists():
            return Response(
                {'error': 'Nenhum dado meteorológico encontrado para o período.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Estatísticas de temperatura
        temp_stats = queryset.aggregate(
            average=Avg('temperature'),
            maximum=Max('temperature'),
            minimum=Min('temperature')
        )
        
        # Estatísticas de umidade
        humidity_avg = queryset.aggregate(average=Avg('humidity'))['average'] or 0
        
        # Estatísticas de vento
        wind_avg = queryset.aggregate(average=Avg('wind_speed'))['average'] or 0
        
        # Condição mais comum
        most_common_condition = queryset.values('main_condition').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        # Contagem por condição
        clear_days = queryset.filter(main_condition='Clear').count()
        rainy_days = queryset.filter(
            main_condition__in=['Rain', 'Drizzle', 'Thunderstorm']
        ).count()
        cloudy_days = queryset.filter(main_condition='Clouds').count()
        
        stats_data = {
            'average_temperature': temp_stats['average'] or 0,
            'max_temperature': temp_stats['maximum'] or 0,
            'min_temperature': temp_stats['minimum'] or 0,
            'average_humidity': humidity_avg,
            'average_wind_speed': wind_avg,
            'most_common_condition': most_common_condition['main_condition'] if most_common_condition else 'Unknown',
            'clear_days': clear_days,
            'rainy_days': rainy_days,
            'cloudy_days': cloudy_days
        }
        
        serializer = WeatherStatsSerializer(stats_data)
        return Response(serializer.data)


class WeatherAlertViewSet(viewsets.ModelViewSet):
    """ViewSet para alertas meteorológicos."""
    
    queryset = WeatherAlert.objects.all()
    serializer_class = WeatherAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtra alertas baseado nos parâmetros da query."""
        queryset = WeatherAlert.objects.all()
        
        # Filtros opcionais
        city = self.request.query_params.get('city')
        country = self.request.query_params.get('country')
        alert_type = self.request.query_params.get('alert_type')
        severity = self.request.query_params.get('severity')
        is_active = self.request.query_params.get('is_active')
        
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        if country:
            queryset = queryset.filter(country__iexact=country)
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Retorna alertas ativos no momento."""
        now = timezone.now()
        active_alerts = self.get_queryset().filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        )
        
        serializer = WeatherAlertSerializer(active_alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Ativa/desativa um alerta."""
        alert = self.get_object()
        alert.is_active = not alert.is_active
        alert.save()
        
        return Response({
            'message': f'Alerta {"ativado" if alert.is_active else "desativado"} com sucesso.',
            'is_active': alert.is_active
        })
