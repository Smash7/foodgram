from django.conf import settings
from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

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
            isnull_value = value == 'no'
            return queryset.filter(recipes__isnull=isnull_value).distinct()
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
            isnull_value = value == 'no'
            return queryset.filter(followers__isnull=isnull_value).distinct()
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
            isnull_value = value == 'no'
            return queryset.filter(authors__isnull=isnull_value).distinct()
        return queryset


@admin.register(FoodgramUser)
class FoodgramUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'get_recipe_count',
        'get_subscription_count', 'get_follower_count'
    )
    search_fields = ('id', 'username', 'email', 'first_name', 'last_name')
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
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            recipe_count=Count('recipes'),
            subscription_count=Count('authors'),
            follower_count=Count('followers')
        )
        return queryset

    def get_recipe_count(self, obj):
        return obj.recipe_count

    get_recipe_count.short_description = 'Количество рецептов'

    def get_subscription_count(self, obj):
        return obj.subscription_count

    get_subscription_count.short_description = 'Количество подписок'

    def get_follower_count(self, obj):
        return obj.follower_count

    get_follower_count.short_description = 'Количество подписчиков'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'recipe__count')
    search_fields = ('id', 'name', 'slug')
    empty_value_display = '-пусто-'


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
            isnull_value = value == 'no'
            return queryset.filter(
                recipe_ingredients__isnull=isnull_value
            ).distinct()
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipes')
    search_fields = ('id', 'name', 'measurement_unit')
    list_filter = (IsIngredientUsedFilter,)
    empty_value_display = '-пусто-'


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time'

    def lookups(self, request, model_admin):
        labels = settings.COOKING_TIME_RANGE.keys()
        return (
            (
                label, settings.COOKING_TIME_MEANS[label]
                .format(self._count_recipes(
                    request,
                    *settings.COOKING_TIME_RANGE[label]
                ))
            )
            for label in labels)

    def queryset(self, request, queryset):
        value = self.value()
        if not settings.COOKING_TIME_RANGE.get(value, None):
            return queryset
        return queryset.filter(
            cooking_time__range=settings.COOKING_TIME_RANGE[value]
        )

    def _count_recipes(self, request, min_time, max_time):
        return self.queryset(request, Recipe.objects.filter(
            cooking_time__range=(min_time, max_time)
        )).count()


class RecipeAuthorFilter(admin.SimpleListFilter):
    title = 'Автор рецепта'
    parameter_name = 'author'

    def lookups(self, request, model_admin):
        return (
            (author.id, author.username)
            for author in FoodgramUser.objects.filter(recipes__isnull=False)
            .distinct()
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(author_id=value)
        return queryset


class RecipeTagFilter(admin.SimpleListFilter):
    title = 'Тег рецепта'
    parameter_name = 'tag'

    def lookups(self, request, model_admin):
        return (
            (tag.id, tag.name)
            for tag in Tag.objects.filter(recipes__isnull=False).distinct()
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(tags__id=value)
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'name', 'image_tag',
                    'cooking_time', 'tag_list', 'ingredient_list')
    search_fields = ('id', 'author__username', 'name',
                     'cooking_time', 'tags__name')
    list_filter = (CookingTimeFilter, RecipeAuthorFilter, RecipeTagFilter)
    empty_value_display = '-пусто-'
    filter_horizontal = ('tags', 'ingredients')

    @admin.display(description='Ингредиенты')
    def ingredient_list(self, obj):
        return mark_safe('<br>'.join(
            f'{ingredient.name}'
            f' {ingredient.recipe_ingredients.get(recipe=obj).amount}'
            f' {ingredient.measurement_unit}'
            for ingredient in obj.ingredients.all()
        ))

    @admin.display(description='Тэги')
    def tag_list(self, obj):
        return mark_safe('<br>'.join(tag.name for tag in obj.tags.all()))

    @admin.display(description='Изображение')
    def image_tag(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="max-height: 100px;'
                ' max-width: 100px;" />')
        return '-'
