from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceStatusViewSet

router = DefaultRouter()
router.register(r'devices', DeviceViewSet)
router.register(r'device-status', DeviceStatusViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
