from django.conf import settings
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
        fields = (*DjoserUserSerializer.Meta.fields, 'is_subscribed', 'avatar')
        read_only_fields = ('is_subscribed', 'avatar')

    def get_is_subscribed(self, user):
        request = self.context.get('request', None)
        return (request and request.user.is_authenticated
                and Subscription.objects.filter(user=request.user,
                                                author=user).exists())


class SimpleRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(ProfileSerializer):
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (*ProfileSerializer.Meta.fields, 'recipe_count')

    def get_recipes(self, recipes_obj):
        request = self.context.get('request')
        return SimpleRecipeSerializer(
            recipes_obj.recipes.all()[:int(
                request.GET.get('recipes_limit', 10**10)
            )], many=True,
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
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(),
                                            source='ingredient.id',
                                            required=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(min_value=settings.INGREDIENT_MIN_AMOUNT,
                                      required=True)

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
    name = serializers.CharField(
        source='name',
        max_length=Recipe._meta.get_field('name').max_length
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('is_favorited', 'is_in_shopping_cart',
                            'id', 'author')

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError("Image is required.")
        return image

    def validate_ingredients(self, ingredients):
        if len(ingredients) == 0:
            raise serializers.ValidationError(
                "Recipe must have at least one ingredient."
            )
        unique = set()
        duplicates = []
        for ingredient_obj in ingredients:
            ingredient_id = ingredient_obj.get('ingredient').get('id')
            if ingredient_id in unique:
                duplicates.append(ingredient_id)
            unique.add(ingredient_id)
        if duplicates:
            raise serializers.ValidationError(
                f"Duplicate item(s): {duplicates}"
            )
        return ingredients

    def validate_tags(self, tags):
        if len(tags) == 0:
            raise serializers.ValidationError(
                "Recipe must have at least one tag."
            )
        unique = set()
        duplicates = []
        for tag in tags:
            if tag in unique:
                duplicates.append(tag)
            unique.add(tag)
        if duplicates:
            raise serializers.ValidationError(
                f"Duplicate item(s): {duplicates}"
            )
        return tags

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['tags'] = TagSerializer(instance.tags.all(), many=True).data
        return data

    def create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data.pop('ingredient')['id'],
                amount=ingredient_data.pop('amount')
            ) for ingredient_data in ingredients_data
        ])

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

        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description',
                                                  instance.description)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        instance.tags.set(tags_data)

        instance.recipe_ingredients.all().delete()
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


class BasketSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        fields = ('recipe', 'user')


class FavoriteSerializer(BasketSerializer):
    class Meta(BasketSerializer.Meta):
        model = FavoriteRecipe
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('user', 'recipe'),
                message='This recipe is already in your favorites.'
            )
        ]

    def to_representation(self, instance):
        return SimpleRecipeSerializer(instance.recipe).data


class ShoppingCartSerializer(BasketSerializer):
    class Meta(BasketSerializer.Meta):
        model = ShoppingCart
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('user', 'recipe'),
                message='This recipe is already in your shopping cart.'
            )
        ]

    def to_representation(self, instance):
        return SimpleRecipeSerializer(instance.recipe).data
