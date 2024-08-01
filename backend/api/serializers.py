from django.contrib.auth import get_user_model
from rest_framework import serializers

from djoser.serializers import (
    UserSerializer as DjoserUserSerializer
)
from drf_extra_fields.fields import Base64ImageField as DrfBase64ImageField

from recipes.models import (
    FavoriteRecipe, Ingredient, Recipe,
    RecipeIngredient, ShoppingCart, Subscription, Tag
)

User = get_user_model()


class ProfileSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = DrfBase64ImageField(max_length=None, use_url=True, required=False)

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = DjoserUserSerializer.Meta.fields + ('is_subscribed', 'avatar')
        read_only_fields = ('is_subscribed', 'avatar')

    def get_is_subscribed(self, user):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user,
                                               author=user).exists()
        return False


class SimpleRecipeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title')

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(ProfileSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes_count')

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, recipes_obj):
        request = self.context.get('request')
        return SimpleRecipeSerializer(
            int(request.GET.get('recipes_limit', 10**10)), many=True,
            context={'request': request}
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    avatar = DrfBase64ImageField()

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
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(min_value=2)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('name', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True, allow_empty=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = ProfileSerializer(read_only=True)
    image = DrfBase64ImageField()
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredient_set', required=True,
        allow_empty=False, allow_null=False
    )
    text = serializers.CharField(source='description')
    name = serializers.CharField(source='title')

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart',
                            'id', 'author')

    def duplicate_validation(self, data, field):
        unique = set()
        duplicates = []
        for item in data:
            if item[field] in unique:
                duplicates.append(item[field])
            else:
                unique.add(item[field])
        if duplicates:
            raise serializers.ValidationError(
                f"Duplicate {field} value(s): {duplicates}"
            )

    def validate_ingredients(self, ingredients):
        if len(ingredients) == 0:
            raise serializers.ValidationError(
                "Recipe must have at least one ingredient "
            )
        self.duplicate_validation(ingredients, 'name')
        return ingredients

    def validate_tags(self, tags):
        if len(tags) == 0:
            raise serializers.ValidationError(
                "Recipe must have at least one tag"
            )
        self.duplicate_validation(tags, 'name')

        return tags

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return data

    def create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(recipe=recipe,
                             ingredient=ingredient_data.pop('id'),
                             **ingredient_data)
            for ingredient_data in ingredients_data)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set', [])
        tags_data = validated_data.pop('tags', [])
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.add(*tags_data)
        self.create_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        super().update(instance, validated_data)
        instance.tags.set(validated_data.get('tags', instance.tags.all()))
        ingredients_data = validated_data.get('recipeingredient_set', None)
        if not ingredients_data:
            raise serializers.ValidationError(
                'Recipe ingredients are required'
            )
        instance.recipeingredient_set.all().delete()
        self.create_ingredients(instance, ingredients_data)

        return instance

    def get_is_favorited(self, recipe):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return recipe.is_favorited(request.user)
        return False

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return recipe.is_in_shopping_cart(request.user)
        return False
