import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import tags from JSON file'
    manage_file = os.path.join(settings.BASE_DIR, 'manage.py')

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to JSON file')

    def handle(self, file, *args, **kwargs):
        os.system(f'python3 {self.manage_file} loaddata {file}')
