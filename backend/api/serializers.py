import base64

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated

from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
    UserSerializer as DjoserUserSerializer
)
from drf_extra_fields.fields import Base64ImageField as DrfBase64ImageField

from .models import (
    FavoriteRecipe, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Subscription, Tag
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

    def to_representation(self, value):
        return 'https://'+settings.ALLOWED_HOSTS[0]+value.url if value else None


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
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, author=obj).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes_limit = int(recipes_limit)
            recipes = obj.recipes.all()[:recipes_limit]
        else:
            recipes = obj.recipes.all()
        return RecipeSimpleSerializer(recipes, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


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
    amount = serializers.IntegerField(min_value=2)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('name', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, allow_empty=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = ProfileSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = RecipeIngredientSerializer(many=True, source='recipeingredient_set', required=True,
                                             allow_empty=False, allow_null=False)
    text = serializers.CharField(source='description')
    name = serializers.CharField(source='title', max_length=256)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart', 'id', 'author')

    def validate(self, data):
        ingredients = data.get('recipeingredient_set', [])
        tags = data.get('tags', [])

        # Check for duplicate ingredients
        unique_ingredients = set()
        for ingredient in ingredients:
            if ingredient['id'] in unique_ingredients:
                raise serializers.ValidationError("Ingredients must be unique.")
            unique_ingredients.add(ingredient['id'])

        # Check for duplicate tags
        unique_tags = set()
        for tag in tags:
            if tag in unique_tags:
                raise serializers.ValidationError("Tags must be unique.")
            unique_tags.add(tag)

        return data

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
        if not validated_data.get('ingredients', None):
            raise serializers.ValidationError('recipe ingredients is required')
        instance.recipeingredient_set.all().delete()
        for ingredient_data in validated_data.get('recipeingredient_set', None):
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
    name = serializers.CharField(source='recipe.title', read_only=True)
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(source='recipe.cooking_time', read_only=True)
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all(), write_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe', 'id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')

    def create(self, validated_data):
        user = self.context['request'].user
        recipe = validated_data.get('recipe')
        shopping_cart, created = ShoppingCart.objects.get_or_create(user=user, recipe=recipe)
        return shopping_cart

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('This recipe is already in your shopping cart')
        return attrs


class ShortLinkSerializer(serializers.Serializer):
    short_link = serializers.URLField()


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all(), write_only=True)

    class Meta:
        model = FavoriteRecipe
        fields = ('user', 'recipe', 'id')
        read_only_fields = ('id',)

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs.get('recipe')
        if FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('This recipe is already in your favorites')
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        favorite_recipe, created = FavoriteRecipe.objects.get_or_create(user=user, recipe=validated_data['recipe'])
        return favorite_recipe

    def to_representation(self, instance):
        return {'id': instance.recipe.id, 'name': instance.recipe.title, 'image': instance.recipe.image.url,
                'cooking_time': instance.recipe.cooking_time}
