from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

UserRelatedField = partial(
    models.ForeignKey,
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    verbose_name='Пользователь',
    blank=False,
    null=False
)
RecipeRelatedField = partial(
    models.ForeignKey,
    'Recipe',
    on_delete=models.CASCADE,
    verbose_name='Рецепт',
    blank=False,
    null=False
)


class FoodgramUser(AbstractUser):
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    USERNAME_FIELD = 'email'
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
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
        ordering = ('first_name',)

    def clean(self):
        super().clean()
        if self.username.lower() == 'me':
            raise ValidationError({'username': 'Username cannot be "me".'})

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
        ordering = ('name',)
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
        ordering = ('name',)
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
        blank=False,
        null=False,
        validators=[MinValueValidator(1)]
    )

    class Meta:
        ordering = ('title',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def is_favorited(self, user):
        return self.recipe_favorites.filter(user=user).exists()

    def is_in_shopping_cart(self, user):
        return self.recipes_in_shopping_cart.filter(user=user).exists()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe,
                               related_name='recipe_ingredients',
                               on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient,
                                   related_name='recipe_ingredients',
                                   on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ('recipe__title',)
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient} в {self.recipe}'


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        blank=False,
        null=False
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        blank=False,
        null=False
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
        return f'{self.user} добавил рецепт "{self.recipe}"'


class FavoriteRecipe(UserRecipeRelation):
    user = UserRelatedField(related_name='user_favorites')
    recipe = RecipeRelatedField(related_name='recipe_favorites')

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        db_table = 'favorite_recipe'


class ShoppingCart(UserRecipeRelation):
    user = UserRelatedField(related_name='user_shopping_cart')
    recipe = RecipeRelatedField(related_name='recipes_in_shopping_cart')

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
        db_table = 'shopping_cart'

    def __str__(self):
        return f'{self.user} добавил в корзину рецепт "{self.recipe}"'
