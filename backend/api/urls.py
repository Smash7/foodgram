from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProfileViewSet

router = DefaultRouter()
router.register(r'users', ProfileViewSet, basename='profile-detail')

djoser_urls = [
    # path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]


urlpatterns = [
    path('', include(router.urls)),
] + djoser_urls

