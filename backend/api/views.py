import hashlib
import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (IsAuthenticated, AllowAny,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from django.http import FileResponse
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
import djoser.views

from .filters import RecipeFilter, SubscriptionFilter
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            ShoppingCart, Subscription, Tag, RecipeIngredient)
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer, IngredientSerializer,
    ProfileSerializer, RecipeSerializer,
    SubscriptionSerializer, TagSerializer, SimpleRecipeSerializer
)
from .utils import generate_shopping_list_text

User = get_user_model()


class ProfileViewSet(djoser.views.UserViewSet):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='me')
    def get_me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=['put', 'delete'],
            permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        if request.method == 'PUT':
            serializer = AvatarSerializer(request.user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            request.user.avatar = None
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def list_subscriptions(self, request):
        subscriptions = self.get_queryset()
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def subscription(self, request, id=None):
        if request.method == 'POST':
            author = get_object_or_404(User, id=id)
            if author == request.user:
                raise ValidationError('Нельзя подписаться на самого себя.')
            elif Subscription.objects.filter(user=request.user,
                                             author=author).exists():
                raise ValidationError(
                    'Вы уже подписаны на этого пользователя.'
                )
            else:
                subscription = Subscription.objects.create(user=request.user,
                                                           author=author)
            return Response(self.get_serializer(subscription.author).data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            get_object_or_404(Subscription, user=request.user,
                              author_id=id).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SubscriptionFilter

    def get_queryset(self):
        return User.objects.filter(authors__user=self.request.user)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsOwnerOrReadOnly, IsAuthenticatedOrReadOnly)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RecipeFilter
    pagination_class = LimitOffsetPagination
    ordering_fields = ('name', 'cooking_time', 'author')
    ordering = ('name',)
    filterset_fields = ('tags__slug', 'author__username',
                        'is_favorited', 'is_in_shopping_cart')

    def collect_basket(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if model.objects.filter(user=request.user, recipe=recipe).exists():
                raise ValidationError('This recipe is already in your list.')
            instance = model.objects.create(user=request.user, recipe=recipe)
            response_serializer = SimpleRecipeSerializer(
                instance.recipe,
                context={'request': request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            get_object_or_404(model, user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite',
            url_name='favorite')
    def favorite(self, request, pk=None):
        return self.collect_basket(request, pk, FavoriteRecipe)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart',
            url_name='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return self.collect_basket(request, pk, ShoppingCart)

    def generate_shopping_list(self, user):
        shopping_cart = ShoppingCart.objects.filter(user=user)

        ingredient_quantities = RecipeIngredient.objects.filter(
            recipe__in=[item.recipe for item in shopping_cart]
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        return generate_shopping_list_text(
            ingredient_quantities,
            shopping_cart.values_list('recipe__name', flat=True)
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart',
            url_name='download_shopping_cart')
    def download_shopping_cart(self, request):
        shopping_list_text = self.generate_shopping_list(request.user)
        return FileResponse(shopping_list_text, as_attachment=True,
                            filename='shopping_list.txt')

    @action(detail=True, methods=['get'], permission_classes=[AllowAny],
            url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        original_url = request.build_absolute_uri(
            reverse('recipe-detail', args=[recipe.id])
        )
        short_url = self.get_short_link(original_url)
        recipe.short_url_hash = short_url
        recipe.save()
        return Response({'short-link': f'https://{settings.ALLOWED_HOSTS[0]}/s'
                                       f'/{short_url}/'})

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
