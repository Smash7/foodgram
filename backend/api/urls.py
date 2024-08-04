from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeViewSet,
                    TagViewSet, ProfileViewSet)


app_name = 'api'

router = DefaultRouter()
router.register(r'users', ProfileViewSet, basename='user-detail')
router.register(r'tags', TagViewSet, basename='tag-detail')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'ingredients', IngredientViewSet,
                basename='ingredient-detail')

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]


