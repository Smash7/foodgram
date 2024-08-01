from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (IsAuthenticated, AllowAny)
from rest_framework.response import Response
from django.http import FileResponse
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.utils import timezone
import hashlib
from rest_framework import serializers
from django.db.models import Sum
import io
import djoser.views



from .filters import RecipeFilter, SubscriptionFilter
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                                    ShoppingCart, Subscription, Tag, RecipeIngredient)
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer, IngredientSerializer,
    ProfileSerializer, RecipeSerializer,
    SubscriptionSerializer, TagSerializer
)

User = get_user_model()


class ProfileViewSet(djoser.views.UserViewSet):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny],
            url_path='me')
    def get_me(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated(
                'Authentication credentials were not provided.'
            )

        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def list_subscriptions(self, request):
        subscriptions = self.get_queryset()
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        if author == request.user:
            raise ValidationError('You cannot subscribe to yourself.')
        elif Subscription.objects.filter(user=request.user,
                                         author=author).exists():
            raise ValidationError('You are already subscribed to this user.')
        else:
            subscription = Subscription.objects.create(user=request.user,
                                                       author=author)
        return Response(self.get_serializer(subscription.author).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def unsubscribe(self, request, id=None):
        get_object_or_404(User, id=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SubscriptionFilter

    def get_queryset(self):
        return User.objects.filter(following__user=self.request.user)


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        request.user.avatar = None
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RecipeFilter
    pagination_class = LimitOffsetPagination
    ordering_fields = ('title', 'cooking_time', 'author')
    ordering = ('title',)
    filterset_fields = ('tags__slug', 'author__username',
                        'is_favorited', 'is_in_shopping_cart')

    def handle_action(request, pk, model, serializer_class):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            data = {'user': request.user.id, 'recipe': recipe.id}
            serializer = serializer_class(data=data,
                                          context={'request': request})
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            response_serializer = serializer_class(
                instance,
                context={'request': request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            model.objects.filter(user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite',
            url_name='favorite')
    def favorite(self, request, pk=None):
        return self.handle_action(request, pk, FavoriteRecipe, RecipeSerializer)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart',
            url_name='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return self.handle_action(request, pk, ShoppingCart, RecipeSerializer)

    def generate_shopping_list(user):
        shopping_cart = ShoppingCart.objects.filter(user=user)

        ingredient_quantities = RecipeIngredient.objects.filter(
            recipe__in=[item.recipe for item in shopping_cart]
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        recipes = shopping_cart.values_list('recipe__title', flat=True)

        date_created = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f'Список покупок составлен: {date_created}\n'
        product_header = 'Продукты:\n'
        products = '\n'.join(
            [
                f'{idx + 1}. {item["ingredient__name"].capitalize()}'
                f' ({item["ingredient__measurement_unit"]})'
                f' -- {item["total_amount"]}'
                for idx, item in enumerate(ingredient_quantities)]
        )
        recipe_header = '\n\nРецепты:\n'
        recipes_list = '\n'.join(
            [f'{idx + 1}. {recipe}' for idx, recipe in enumerate(recipes)]
        )

        return '\n'.join([header, product_header, products,
                          recipe_header, recipes_list])

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart',
            url_name='download_shopping_cart')
    def download_shopping_cart(self, request):
        shopping_list_text = self.generate_shopping_list(request.user)

        buffer = io.BytesIO()
        buffer.write(shopping_list_text.encode('utf-8'))
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True,
                            filename='shopping_list.txt')

    @action(detail=True, methods=['get'], permission_classes=[AllowAny],
            url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        original_url = request.build_absolute_uri(reverse('recipe-detail',
                                                          args=[recipe.id]))
        short_url = self.get_short_link(original_url)
        return Response({'short-link': original_url + short_url})

    def get_short_link(self, url):
        return hashlib.md5(url.encode()).hexdigest()[:8]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None
