import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Импорт ингредиентов из data/ingredients.json'

    def handle(self, *args, **kwargs):
        file_path = os.path.join(
            settings.BASE_DIR.parent,
            'data/ingredients.json'
        )
        call_command('loaddata', file_path)
