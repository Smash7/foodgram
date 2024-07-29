import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import Recipe, Tag

User = get_user_model()


class RecipeFilter(django_filters.rest_framework.FilterSet):
    is_favorited = django_filters.rest_framework.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.rest_framework.BooleanFilter(method='filter_is_in_shopping_cart')
    tags = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False
    )

    class Meta:
        model = Recipe
        fields = ['tags', 'author', 'is_favorited', 'is_in_shopping_cart']

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.filter(in_shopping_cart__user=user)
        return queryset


class SubscriptionFilter(django_filters.FilterSet):
    recipes_limit = django_filters.NumberFilter(method='filter_recipes_limit')

    class Meta:
        model = User
        fields = []

    def filter_recipes_limit(self, queryset, name, value):
        if value is not None:
            queryset = queryset.annotate(recipes_count=Count('recipes')).filter(recipes_count__lte=value)
        return queryset
