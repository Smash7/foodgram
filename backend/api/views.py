from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import Tag, Recipe, Ingredient, ShoppingCart
from .pagination import LimitPagination
from .serializers import AvatarSerializer, ProfileSerializer, TagSerializer, RecipeSerializer, IngredientSerializer, ShoppingCartSerializer
from .filters import RecipeFilter

User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('avatar')
    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RecipeFilter
    pagination_class = LimitOffsetPagination
    ordering_fields = ('title', 'cooking_time', 'author')
    ordering = ('title',)
    filterset_fields = ('tags__slug', 'author__username', 'is_favorited', 'is_in_shopping_cart')


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


class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download(self, request):
        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        shopping_list = {}
        for item in shopping_cart:
            for ingredient in item.recipe.recipeingredient_set.all():
                if ingredient.ingredient.name in shopping_list:
                    shopping_list[ingredient.ingredient.name] += ingredient.amount
                else:
                    shopping_list[ingredient.ingredient.name] = ingredient.amount

        shopping_list_text = '\n'.join([f'{name} - {amount}' for name, amount in shopping_list.items()])

        response = Response(shopping_list_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_recipe(self, request, pk=None):
        recipe = Recipe.objects.get(pk=pk)
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_recipe(self, request, pk=None):
        recipe = Recipe.objects.get(pk=pk)
        ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
