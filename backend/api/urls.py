from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AvatarUploadView, IngredientViewSet, RecipeViewSet,
                    SubscriptionViewSet, TagViewSet, ProfileViewSet)


router = DefaultRouter()
router.register(r'users', ProfileViewSet, basename='user-detail')
router.register(r'tags', TagViewSet, basename='tag-detail')
router.register(r'recipes', RecipeViewSet, basename='recipe-detail')
router.register(r'ingredients', IngredientViewSet,
                basename='ingredient-detail')
router.register(r'users/subscriptions', SubscriptionViewSet,
                basename='subscription')


urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('', include(router.urls)),
    # path('', include('djoser.urls')),
]
