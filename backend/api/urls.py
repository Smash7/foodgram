from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AvatarUploadView, IngredientViewSet, RecipeViewSet, SubscriptionViewSet, TagViewSet
router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag-detail')
router.register(r'recipes', RecipeViewSet, basename='recipe-detail')
router.register(r'ingredients', IngredientViewSet, basename='ingredient-detail')
router.register(r'users/subscriptions', SubscriptionViewSet, basename='subscription')

djoser_urls = [
    path('', include('djoser.urls')),
    path('users/<int:id>/subscribe/', SubscriptionViewSet.as_view({'post': 'subscribe'}), name='user-subscribe'),
    path('users/<int:id>/unsubscribe/',
         SubscriptionViewSet.as_view({'delete': 'unsubscribe'}),
         name='user-unsubscribe'),
    path('auth/', include('djoser.urls.authtoken')),
]


urlpatterns = [
    path('users/me/avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('', include(router.urls)),
] + djoser_urls
