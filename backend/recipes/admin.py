from django.contrib import admin

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
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)
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
        if self.value() == 'yes':
            return queryset.filter(follower__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(follower__isnull=True)
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

    def has_recipes(self, obj):
        return obj.recipes.exists()
    has_recipes.boolean = True
    has_recipes.short_description = 'Есть рецепты'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('id', 'name', 'slug')
    empty_value_display = '-пусто-'
    ordering = ('id',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('id', 'name', 'measurement_unit')
    list_filter = ('id', 'name', 'measurement_unit')
    empty_value_display = '-пусто-'
    ordering = ('id',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'title', 'image',
                    'description', 'cooking_time')
    search_fields = ('id', 'author', 'title', 'description', 'cooking_time')
    list_filter = ('id', 'author', 'title', 'description', 'cooking_time')
    empty_value_display = '-пусто-'
    ordering = ('id',)
    filter_horizontal = ('tags', 'ingredients')
