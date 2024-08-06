from django.http import Http404
from django.shortcuts import redirect

from .models import Recipe


def short_url_redirect(request, pk):
    if not Recipe.objects.filter(pk=pk).exists():
        raise Http404(f'Рецепт с id {pk} не найден.')
    return redirect('api:recipe-detail', pk=pk)
