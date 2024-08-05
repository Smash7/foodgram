from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (IsAuthenticated, AllowAny,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from django.http import FileResponse
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
import djoser.views

from .filters import RecipeFilter, IngredientFilter
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            ShoppingCart, Subscription, Tag, RecipeIngredient)
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer, IngredientSerializer,
    ProfileSerializer, RecipeSerializer,
    TagSerializer, SimpleRecipeSerializer
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

            subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author
            )
            if not created:
                raise ValidationError(
                    'Вы уже подписаны на этого пользователя.'
                )
            return Response(self.get_serializer(subscription.author).data,
                            status=status.HTTP_201_CREATED)

        get_object_or_404(Subscription, user=request.user,
                          author_id=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def post_delete_recipe_to_basket(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            _, created = model.objects.get_or_create(user=request.user,
                                                     recipe=recipe)
            if not created:
                raise ValidationError('Рецепт уже добавлен в корзину.')
            return Response(
                SimpleRecipeSerializer(recipe,
                                       context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            model.objects.filter(user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite',
            url_name='favorite')
    def favorite(self, request, pk=None):
        return self.post_delete_recipe_to_basket(request, pk, FavoriteRecipe)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart',
            url_name='shopping_cart')
    def shopping_cart(self, request, pk=None):
        return self.post_delete_recipe_to_basket(request, pk, ShoppingCart)

    def generate_shopping_list(self, user):
        shopping_cart = ShoppingCart.objects.filter(user=user).all()

        ingredient_quantities = RecipeIngredient.objects.filter(
            recipe__in=[cart.recipe for cart in shopping_cart]
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        return generate_shopping_list_text(
            ingredient_quantities,
            shopping_cart
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart',
            url_name='download_shopping_cart')
    def download_shopping_cart(self, request):
        return FileResponse(
            self.generate_shopping_list(request.user),
            as_attachment=True,
            filename='shopping_list.txt'
        )

    @action(detail=True, methods=['get'], permission_classes=[AllowAny],
            url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(reverse(
            'shortener:short-link-redirect',
            args=[recipe.short_url_hash]
        ))
        return Response({'short-link': short_link})


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
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
