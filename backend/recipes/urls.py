from django.urls import path

from .views import short_url_redirect

app_name = 'recipes'

urlpatterns = [
    path('<int:pk>/', short_url_redirect, name='short-link-redirect'),
]
