from django.urls import path

from .views import ShortUrlView

urlpatterns = [
    path(
        '<str:short_url_hash>/',
        ShortUrlView.as_view(),
        name='short-link-redirect'
    ),
]
