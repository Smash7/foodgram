from django.contrib import admin

from .models import FoodgramUser, Ingredient, Recipe, Tag


@admin.register(FoodgramUser)
class FoodgramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff', 'is_active', 'recipe_count',
                    'subscription_count', 'follower_count')
    search_fields = ('id', 'username', 'email', 'first_name', 'last_name')
    list_filter = ('id', 'username', 'email', 'first_name',
                   'last_name', 'is_staff', 'is_active')
    empty_value_display = '-пусто-'
    ordering = ('id',)
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
    list_filter = ('id', 'name', 'slug')
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
