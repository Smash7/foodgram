from django.shortcuts import get_object_or_404, redirect, reverse
from rest_framework.views import View

from .models import Recipe


class ShortUrlView(View):
    def get(self, request, short_url_hash):
        recipe = get_object_or_404(Recipe, short_url_hash=short_url_hash)
        return redirect(reverse('recipe-detail', args=[recipe.id]))
