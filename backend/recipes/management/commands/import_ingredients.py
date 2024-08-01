import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import ingredients from data/ingredients.json'
    manage_file = os.path.join(settings.BASE_DIR, 'manage.py')
    file = os.path.join(settings.BASE_DIR.parent, 'data/ingredients.json')

    def handle(self, *args, **kwargs):
        os.system(f'python3 {self.manage_file} loaddata {self.file}')
