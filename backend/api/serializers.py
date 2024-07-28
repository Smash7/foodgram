import base64

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated
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

    def to_representation(self, instance):
        request = self.context.get('request', None)
        if request and not request.user.is_authenticated and request.path == '/api/users/me/':
            raise NotAuthenticated('Authentication credentials were not provided.')
        return super().to_representation(instance)

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

class RecipeSimpleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title')
    image = DrfBase64ImageField(use_url=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

class SubscriptionSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = DrfBase64ImageField(max_length=None, use_url=True, required=False)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, author=obj).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()  # You can add filters or pagination here if needed
        return RecipeSimpleSerializer(recipes, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('avatar',)

    def get_avatar(self, obj):
        request = self.context.get('request')
        if request is not None and obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url)
        elif obj.avatar and hasattr(obj.avatar, 'url'):
            domain = settings.DEFAULT_DOMAIN
            protocol = settings.DEFAULT_PROTOCOL
            return f"{protocol}://{domain}{obj.avatar.url}"
        return None

    def to_internal_value(self, data):
        if 'avatar' in data and isinstance(data['avatar'], str):
            data['avatar'] = Base64ImageField(required=True).to_internal_value(data['avatar'])
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        avatar = validated_data.pop('avatar', None)
        if avatar:
            instance.avatar = avatar
        else:
            raise serializers.ValidationError('avatar is required')

        return super().update(instance, validated_data)


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
        read_only_fields = ('name', 'measurement_unit')


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
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart', 'id', 'author')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return data

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

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        instance.image = validated_data.get('image', instance.image)
        instance.save()
        instance.tags.set(validated_data.get('tags', instance.tags.all()))
        instance.recipeingredient_set.all().delete()
        for ingredient_data in validated_data.get('recipeingredient_set', []):
            ingredient = ingredient_data.pop('id')
            RecipeIngredient.objects.create(recipe=instance, ingredient=ingredient, **ingredient_data)
        return instance

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


class ShortLinkSerializer(serializers.Serializer):
    short_link = serializers.URLField()