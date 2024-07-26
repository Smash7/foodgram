import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField as DrfBase64ImageField

from .models import Subscription, Tag, Recipe, FavoriteRecipe, ShoppingCart, Ingredient, RecipeIngredient
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
    UserSerializer as DjoserUserSerializer
)

User = get_user_model()


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'username', 'password')


class ProfileSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = DrfBase64ImageField(max_length=None, use_url=True, required=False)

    def get_is_subscribed(self, obj):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, author=obj).exists()
        return False

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')
        read_only_fields = ('is_subscribed', 'avatar')


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('avatar', 'avatar_url')

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('slug', 'name')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('name',)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit', read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = ProfileSerializer(read_only=True)
    image = Base64ImageField(required=False, allow_null=True)
    ingredients = RecipeIngredientSerializer(many=True, source='recipeingredient_set')
    text = serializers.CharField(source='description')
    name = serializers.CharField(source='title')

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text',
            'cooking_time', 'is_favorited', 'is_in_shopping_cart',
            'author', 'id'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart', 'id', 'author')

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set')
        tags_data = validated_data.pop('tags', [])
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author, **validated_data)

        for tag in tags_data:
            recipe.tags.add(tag)

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.pop('id')
            RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, **ingredient_data)

        return recipe

    def get_is_favorited(self, obj):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return obj.is_favorited(request.user)
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return obj.is_in_shopping_cart(request.user)
        return False


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('id', 'user', 'recipe')
        read_only_fields = ('user',)
