import django_filters

from .models import Recipe, Tag

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
