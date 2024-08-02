from django.contrib import admin
from django.utils.html import format_html

from .models import FoodgramUser, Ingredient, Recipe, Tag


class HasRecipesFilter(admin.SimpleListFilter):
    name = 'Есть рецепты'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    name = 'Есть подписки'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(follower__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(follower__isnull=True)
        return queryset


class HasFollowersFilter(admin.SimpleListFilter):
    name = 'Есть подписчики'
    parameter_name = 'has_followers'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(following__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(following__isnull=True)
        return queryset


@admin.register(FoodgramUser)
class FoodgramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff', 'is_active', 'recipe_count',
                    'subscription_count', 'follower_count')
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


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('id', 'name', 'slug')
    empty_value_display = '-пусто-'
    ordering = ('id',)


class IsIngredientUsedFilter(admin.SimpleListFilter):
    name = 'Используется в рецептах'
    parameter_name = 'is_ingredient_used'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(ingredients__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(ingredients__isnull=True)
        return queryset


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit', 'recipes')
    search_fields = ('id', 'name', 'measurement_unit')
    list_filter = (IsIngredientUsedFilter,)
    empty_value_display = '-пусто-'


class CookingTimeFilter(admin.SimpleListFilter):
    name = 'Cooking Time'
    parameter_name = 'cooking_time'

    def lookups(self, request, model_admin):
        return (
            ('fast', 'быстрее 15 мин ({})'.format(
                self._count_recipes(request, 0, 15)
            )),
            ('medium', 'быстрее 30 мин ({})'.format(
                self._count_recipes(request, 15, 30)
            )),
            ('long', 'долго ({})'.format(
                self._count_recipes(request, 30, None)
            )),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'fast':
            return queryset.filter(cooking_time__lt=15)
        if value == 'medium':
            return queryset.filter(cooking_time__gte=15, cooking_time__lt=30)
        if value == 'long':
            return queryset.filter(cooking_time__gte=30)
        return queryset

    def _count_recipes(self, request, min_time, max_time):
        queryset = self.queryset(request, Recipe.objects.all())
        if min_time is not None:
            queryset = queryset.filter(cooking_time__gte=min_time)
        if max_time is not None:
            queryset = queryset.filter(cooking_time__lt=max_time)
        return queryset.count()


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'name', 'image_tag',
                    'description', 'cooking_time', 'tag_list',
                    'ingredient_list')
    search_fields = ('id', 'author__username', 'name', 'description',
                     'cooking_time', 'tags__name')
    list_filter = (CookingTimeFilter,)
    empty_value_display = '-пусто-'
    filter_horizontal = ('tags', 'ingredients')

    def ingredient_list(self, obj):
        return (', '.join(ingredient.name for
                          ingredient in obj.ingredients.all()))

    def tag_list(self, obj):
        return ', '.join(tag.name for tag in obj.tags.all())

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px;'
                ' max-width: 100px;" />', obj.image.url)
        return '-'

    image_tag.short_description = 'Image'
