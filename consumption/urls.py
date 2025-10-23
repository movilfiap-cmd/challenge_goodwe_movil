from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsumptionReadingViewSet, ConsumptionLimitViewSet, ConsumptionAlertViewSet
)

router = DefaultRouter()
router.register(r'readings', ConsumptionReadingViewSet)
router.register(r'limits', ConsumptionLimitViewSet)
router.register(r'alerts', ConsumptionAlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
