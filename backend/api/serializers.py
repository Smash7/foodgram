from collections import Counter

from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import (
    UserSerializer as DjoserUserSerializer
)
from drf_extra_fields.fields import Base64ImageField as DrfBase64ImageField

from recipes import constants
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
        fields = (*DjoserUserSerializer.Meta.fields, 'is_subscribed', 'avatar')
        read_only_fields = ('is_subscribed', 'avatar')

    def get_is_subscribed(self, user):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and Subscription.objects.filter(user=request.user,
                                                author=user).exists())


class SimpleRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(ProfileSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (*ProfileSerializer.Meta.fields, 'recipes_count', 'recipes')

    def get_recipes(self, user):
        request = self.context.get('request')
        return SimpleRecipeSerializer(
            user.recipes.all()[:int(
                request.GET.get('recipes_limit', 10**10)
            )], many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, user):
        return user.recipes.count()


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
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(),
                                            source='ingredient.id',
                                            required=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(
        min_value=constants.MIN_INGREDIENT_AMOUNT,
        required=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True,
                                              allow_empty=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = ProfileSerializer(read_only=True)
    image = DrfBase64ImageField()
    ingredients = RecipeIngredientSerializer(many=True,
                                             source='recipe_ingredients',
                                             required=True, allow_empty=False,
                                             allow_null=False)
    text = serializers.CharField(source='description')

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart',
                            'id', 'author')

    @staticmethod
    def tags_or_ingredients_validation(
            tags_or_ingredients,
            field_name,
            model_class
    ):
        if not tags_or_ingredients:
            raise serializers.ValidationError({
                field_name: 'Рецепт должен содержать хотя бы один элемент'
            })
        names = {item.name for item in tags_or_ingredients}
        existing_names = set(model_class.objects.filter(name__in=names)
                             .values_list('name', flat=True))
        missing_names = names - existing_names

        if missing_names:
            raise serializers.ValidationError({
                field_name: f'Некоторые элементы не существуют:'
                            f' {missing_names}.'
            })

        duplicates = [item_id for item_id, count in Counter(names).items()
                      if count > 1]
        if duplicates:
            raise serializers.ValidationError({
                field_name: f'Элементы не должны дублироваться'
                            f' в одном рецепте: {duplicates}.'
            })

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError('Изображение не выбрано.')
        return image

    def validate_ingredients(self, ingredients):
        self.tags_or_ingredients_validation(
            [ingredient.get('ingredient').get('id')
             for ingredient in ingredients],
            'ingredients', Ingredient)
        return ingredients

    def validate_tags(self, tags):
        self.tags_or_ingredients_validation(tags, 'tags', Tag)
        return tags

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return data

    def create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data.pop('ingredient')['id'],
                amount=ingredient_data.pop('amount')
            ) for ingredient_data in ingredients_data
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags_data = validated_data.pop('tags', [])
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        self.validate_ingredients(ingredients_data)
        tags_data = validated_data.pop('tags', [])
        self.validate_tags(tags_data)

        instance.tags.set(tags_data)

        instance.recipe_ingredients.all().delete()
        self.create_ingredients(instance, ingredients_data)

        return super().update(instance, validated_data)

    def get_is_favorited(self, recipe):
        request = self.context.get('request')
        return (request
                and request.user.is_authenticated
                and FavoriteRecipe.objects.filter(user=request.user,
                                                  recipe=recipe).exists())

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get('request')

        return (request
                and request.user.is_authenticated
                and ShoppingCart.objects.filter(user=request.user,
                                                recipe=recipe).exists())
