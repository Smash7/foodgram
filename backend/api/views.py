import requests
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
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError


from .filters import RecipeFilter, SubscriptionFilter
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                                    ShoppingCart, Subscription, Tag)
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AvatarSerializer, FavoriteRecipeSerializer, IngredientSerializer,
    ProfileSerializer, RecipeSerializer, ShoppingCartSerializer,
    ShortLinkSerializer, SubscriptionSerializer, TagSerializer
)

User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('avatar')
    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny],
            url_path='me')
    def get_me(self, request):
        if not request.user.is_authenticated:
            raise NotAuthenticated(
                'Authentication credentials were not provided.'
            )

        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SubscriptionFilter

    def get_queryset(self):
        return User.objects.filter(following__user=self.request.user)

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
        if Subscription.objects.filter(user=request.user,
                                       author=author).exists():
            return Response(
                {'detail': 'You are already subscribed to this user.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if author == request.user:
            return Response(
                {'detail': 'You cannot subscribe to yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = Subscription.objects.create(user=request.user,
                                                   author=author)
        serializer = self.get_serializer(subscription.author)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def unsubscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        subscription = Subscription.objects.filter(user=request.user,
                                                   author=author).first()
        if not subscription:
            return Response(
                {'detail': 'You are not subscribed to this user.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        user = request.user
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsOwnerOrReadOnly, IsAuthenticated)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RecipeFilter
    pagination_class = LimitOffsetPagination
    ordering_fields = ('title', 'cooking_time', 'author')
    ordering = ('title',)
    filterset_fields = ('tags__slug', 'author__username',
                        'is_favorited', 'is_in_shopping_cart')

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated],
            url_path='favorite', url_name='favorite')
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            favorite_recipe_data = {'user': request.user.id,
                                    'recipe': recipe.id}
            serializer = FavoriteRecipeSerializer(data=favorite_recipe_data,
                                                  context={'request': request})
            serializer.is_valid(raise_exception=True)
            favorite_recipe = serializer.save()
            response_serializer = ShoppingCartSerializer(
                favorite_recipe,
                context={'request': request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            FavoriteRecipe.objects.filter(user=request.user,
                                          recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated],
            url_path='download_shopping_cart',
            url_name='download_shopping_cart')
    def download_shopping_cart(self, request):
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        shopping_list = {}
        for item in shopping_cart:
            for ingredient in item.recipe.recipeingredient_set.all():
                if ingredient.ingredient.name in shopping_list:
                    shopping_list[ingredient.ingredient.name] += (
                        ingredient.amount
                    )
                else:
                    shopping_list[ingredient.ingredient.name] = (
                        ingredient.amount
                    )

        shopping_list_text = ('\n'.join([f'- {name} -- {amount}'
                                         for name, amount
                                         in shopping_list.items()]))
        response = Response(shopping_list_text, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart',
            url_name='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            shopping_cart_data = {'user': request.user.id, 'recipe': recipe.id}
            serializer = ShoppingCartSerializer(data=shopping_cart_data,
                                                context={'request': request})
            serializer.is_valid(raise_exception=True)
            shopping_cart = serializer.save()
            response_serializer = ShoppingCartSerializer(
                shopping_cart,
                context={'request': request}
            )
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            ShoppingCart.objects.filter(user=request.user,
                                        recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'],
            permission_classes=[permissions.AllowAny], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        original_url = (
            f'https://{settings.ALLOWED_HOSTS[0]}/recipes/{recipe.id}/'
        )
        short_url = self.get_short_link(original_url)
        if short_url:
            serializer = ShortLinkSerializer({'short_link': short_url})
            return Response(serializer.data)
        return Response({'error': 'Could not generate short link'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart',
            url_name='shopping_cart')
    def manage_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError(
                    'This recipe is already in your shopping cart'
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response({
                'id': recipe.id,
                'name': recipe.title,
                'image': recipe.image.url,
                'cooking_time': recipe.cooking_time
            }, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            shopping_cart_item = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if shopping_cart_item:
                shopping_cart_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            raise ValidationError('This recipe is not in your shopping cart')

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite',
            url_name='favorite')
    def manage_favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            if FavoriteRecipe.objects.filter(
                    user=user,
                    recipe=recipe
            ).exists():
                raise ValidationError(
                    'This recipe is already in your favorites'
                )
            FavoriteRecipe.objects.create(user=user, recipe=recipe)
            return Response({
                'id': recipe.id,
                'name': recipe.title,
                'image': recipe.image.url,
                'cooking_time': recipe.cooking_time
            }, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite_recipe = FavoriteRecipe.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if favorite_recipe:
                favorite_recipe.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            raise ValidationError('This recipe is not in your favorites')

    def get_short_link(self, url):
        clck_url = f'https://clck.ru/--?url={url}'
        response = requests.get(clck_url)
        if response.status_code == 200:
            return response.text
        return None


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
