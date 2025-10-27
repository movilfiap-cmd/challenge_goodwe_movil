from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsumptionReadingViewSet, ConsumptionLimitViewSet, ConsumptionAlertViewSet,
    EnergyProductionViewSet, SolarPanelViewSet, EnergyManagementConfigViewSet
)

router = DefaultRouter()
router.register(r'readings', ConsumptionReadingViewSet)
router.register(r'limits', ConsumptionLimitViewSet)
router.register(r'alerts', ConsumptionAlertViewSet)
router.register(r'production', EnergyProductionViewSet)
router.register(r'solar-panels', SolarPanelViewSet)
router.register(r'energy-config', EnergyManagementConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
