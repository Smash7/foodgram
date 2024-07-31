from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class FoodgramUser(AbstractUser):
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
        blank=False,
        null=False
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
        blank=False,
        null=False
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
        blank=False,
        null=False
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
        ordering = ('id',)

    def recipe_count(self):
        return self.recipes.count()

    def subscription_count(self):
        return self.following.count()

    def follower_count(self):
        return self.follower.count()

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
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
        max_length=200,
        verbose_name='Название ингредиента',
        blank=False,
        null=False
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения',
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Tag(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Название тэга'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Slug'
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    title = models.CharField(
        max_length=256,
        verbose_name='Название рецепта',
        blank=False,
        null=False
    )
    image = models.ImageField(
        upload_to='recipes/',
        blank=False,
        null=False,
        verbose_name='Фото блюда'
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=False,
        null=False
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления',
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def is_favorited(self, user):
        return self.favorited_by.filter(user=user).exists()

    def is_in_shopping_cart(self, user):
        return self.in_shopping_cart.filter(user=user).exists()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        unique_together = ('recipe', 'ingredient')


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь',
        blank=False,
        null=False
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Рецепт',
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в избранное рецепт "{self.recipe}"'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь',
        blank=False,
        null=False
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
        verbose_name='Рецепт',
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в корзину рецепт "{self.recipe}"'
