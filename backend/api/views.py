from rest_framework import viewsets
from rest_framework import permissions
from django.contrib.auth import get_user_model

from .serializers import ProfileSerializer


User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().prefetch_related('follower', 'following')
    serializer_class = ProfileSerializer
    # permission_classes = (permissions.IsAuthenticated,)
