from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tag
from .serializers import AvatarSerializer, ProfileSerializer, TagSerializer

User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().prefetch_related('follower', 'following')
    serializer_class = ProfileSerializer
    # permission_classes = (permissions.IsAuthenticated,)


class AvatarUploadView(APIView):
    def put(self, request, *args, **kwargs):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None