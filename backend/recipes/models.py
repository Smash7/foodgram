from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from . import constants
from . import validators


class FoodgramUser(AbstractUser):
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    USERNAME_FIELD = 'email'
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Юзернейм',
        validators=[validators.validate_username]
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
        max_length=254
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
    )
    avatar = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to='avatars/',
        verbose_name='Аватар'
    )

    class Meta(AbstractUser.Meta):
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('email',)

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=32,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=32,
        unique=True,
        verbose_name='Слаг'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        max_length=256,
        verbose_name='Название',
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Фото блюда'
    )
    description = models.TextField(
        verbose_name='Описание',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
        related_name='recipes'
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления (минуты)',
        validators=[MinValueValidator(constants.MIN_COOKING_TIME)]
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(constants.MIN_INGREDIENT_AMOUNT)],
        verbose_name='Количество'
    )

    class Meta:
        ordering = ('recipe__name',)
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        return f'{self.ingredient} в {self.recipe}'


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='%(class)ss'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='%(class)ss'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(class)s_unique_user_recipe'
            )
        ]

    def __str__(self):
        return (f'{self.user} добавил рецепт "{self.recipe}" в'
                f' "{self._meta.verbose_name_plural}"')


class FavoriteRecipe(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
