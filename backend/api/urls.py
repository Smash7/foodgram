from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TagViewSet, AvatarUploadView, RecipeViewSet, IngredientViewSet

router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag-detail')
router.register(r'recipes', RecipeViewSet, basename='recipe-detail')
router.register(r'ingredients', IngredientViewSet, basename='ingredient-detail')

djoser_urls = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]


urlpatterns = [
    path('users/me/avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('', include(router.urls)),
] + djoser_urls

