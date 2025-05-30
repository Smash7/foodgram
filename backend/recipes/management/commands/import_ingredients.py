import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из data/ingredients.json'

    def handle(self, *args, **kwargs):
        file_path = os.path.join(settings.BASE_DIR.parent,
                                 'data/ingredients.json')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден'))
            return

        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            Ingredient.objects.bulk_create([
                Ingredient(**item) for item in data
            ])

        self.stdout.write(self.style
                          .SUCCESS('Ингредиенты успешно импортированы'))
