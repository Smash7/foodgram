from django.contrib import admin
from django.urls import reverse
from django.db.models import Count
from django.utils.safestring import mark_safe

from . import constants
from .models import FoodgramUser, Ingredient, Recipe, Tag


class HasRecipesFilter(admin.SimpleListFilter):
    title = 'Есть рецепты'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value in ('yes', 'no'):
            return (queryset.filter(recipes__isnull=value == 'no')
                    .distinct())
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = 'Есть подписки'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value in ('yes', 'no'):
            return (queryset.filter(followers__isnull=value == 'no')
                    .distinct())
        return queryset


class HasFollowersFilter(admin.SimpleListFilter):
    title = 'Есть подписчики'
    parameter_name = 'has_followers'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value in ('yes', 'no'):
            return (queryset.filter(authors__isnull=value == 'no')
                    .distinct())
        return queryset


@admin.register(FoodgramUser)
class FoodgramUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'get_recipe_count',
        'get_subscription_count', 'get_follower_count'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = (HasRecipesFilter, HasSubscriptionsFilter,
                   HasFollowersFilter)
    empty_value_display = '-пусто-'
    readonly_fields = ('avatar',)
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'first_name',
                       'last_name', 'avatar')
        }),
        ('Права доступа', {
            'fields': ('is_staff', 'is_active')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipe_count=Count('recipes'),
            subscription_count=Count('authors'),
            follower_count=Count('followers')
        )

    @mark_safe
    @admin.display(description='Рецепты')
    def get_recipe_count(self, obj):
        count = obj.recipe_count
        if count > 0:
            url = (reverse('admin:recipes_recipe_changelist')
                   + f'?author__id__exact={obj.id}')
            return f'<a href="{url}">{count}</a>'
        return count

    @admin.display(description='Подписки')
    def get_subscription_count(self, user):
        return user.subscription_count

    @admin.display(description='Подписчики')
    def get_follower_count(self, user):
        return user.follower_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'get_recipe_count')
    search_fields = ('name', 'slug')
    empty_value_display = '-пусто-'

    @admin.display(description='Рецепты')
    def get_recipe_count(self, tag):
        return tag.recipes.count()


class IsIngredientUsedFilter(admin.SimpleListFilter):
    title = 'Используется в рецептах'
    parameter_name = 'is_ingredient_used'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value in ('yes', 'no'):
            return queryset.filter(
                recipe_ingredients__isnull=value == 'no'
            ).distinct()
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipes')
    search_fields = ('name', 'measurement_unit')
    list_filter = (IsIngredientUsedFilter,)
    empty_value_display = '-пусто-'


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time'

    COOKING_TIME_RANGE = {
        'fast': (0, constants.LOWER_COOKING_TIME_TRESHOLD),
        'medium': (constants.LOWER_COOKING_TIME_TRESHOLD,
                   constants.UPPER_COOKING_TIME_TRESHOLD),
        'long': (constants.UPPER_COOKING_TIME_TRESHOLD, 10 ** 10)
    }
    COOKING_TIME_MEANS = {
        'fast': f'быстрее {constants.LOWER_COOKING_TIME_TRESHOLD} минут'
                + ' ({})',
        'medium': f'быстрее {constants.UPPER_COOKING_TIME_TRESHOLD} минут'
                  + ' ({})',
        'long': f'дольше {constants.UPPER_COOKING_TIME_TRESHOLD} минут'
                + ' ({})'
    }

    def lookups(self, request, model_admin):
        labels = self.COOKING_TIME_RANGE.keys()
        return (
            (
                label, self.COOKING_TIME_MEANS[label]
                .format(self.filter_by_cooking_time(
                    self.queryset(request, Recipe.objects.all()),
                    *self.COOKING_TIME_RANGE[label]
                ).count())
            ) for label in labels
        )

    def queryset(self, request, queryset):
        time_range = self.COOKING_TIME_RANGE.get(self.value())
        if not time_range:
            return queryset
        return self.filter_by_cooking_time(queryset, *time_range)

    def filter_by_cooking_time(self, queryset, min_time, max_time):
        return queryset.filter(cooking_time__range=(min_time, max_time))


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'name', 'image_tag',
                    'cooking_time', 'tag_list', 'ingredient_list')
    search_fields = ('id', 'author__username', 'name',
                     'cooking_time', 'tags__name')
    list_filter = (CookingTimeFilter, 'tags', 'author', 'ingredients')
    empty_value_display = '-пусто-'
    filter_horizontal = ('tags', 'ingredients')

    @mark_safe
    @admin.display(description='Ингредиенты')
    def ingredient_list(self, recipe):
        ingredients = (recipe.recipe_ingredients
                       .select_related('ingredient').all())
        return '<br>'.join(
            f'{ingredient.ingredient.name} {ingredient.amount}'
            f' {ingredient.ingredient.measurement_unit}'
            for ingredient in ingredients
        )

    @mark_safe
    @admin.display(description='Тэги')
    def tag_list(self, recipe):
        return '<br>'.join(tag.name for tag in recipe.tags.all())

    @mark_safe
    @admin.display(description='Изображение')
    def image_tag(self, recipe):
        if recipe.image:
            return (
                f'<img src="{recipe.image.url}" style="max-height: 100px;'
                ' max-width: 100px;" />')
        return '-'
