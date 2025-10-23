from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WeatherForecastViewSet, WeatherAlertViewSet

router = DefaultRouter()
router.register(r'forecasts', WeatherForecastViewSet)
router.register(r'alerts', WeatherAlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
