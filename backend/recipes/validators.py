import re

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_username(username):
    if username == settings.AUTH_USER_PATH:
        raise ValidationError(
            f'Имя пользователя не может быть "{settings.AUTH_USER_PATH}".'
        )
    invalid_chars = re.findall(r'[^\w.@+-]', username)
    if invalid_chars:
        raise ValidationError(
            f'Имя пользователя не должно содержать символы:'
            f' {"".join(set(invalid_chars))}'
        )
