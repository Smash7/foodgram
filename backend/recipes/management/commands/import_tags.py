import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import tags from data/tags.json'
    manage_file = os.path.join(settings.BASE_DIR, 'manage.py')
    file = os.path.join(settings.BASE_DIR.parent, 'data/tags.json')

    def handle(self, *args, **kwargs):
        os.system(f'python3 {self.manage_file} loaddata {self.file}')
