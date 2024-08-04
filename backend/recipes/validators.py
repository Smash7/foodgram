import re

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_username(username):
    if username == settings.AUTH_USER_PATH:
        raise ValidationError(
            f"Username cannot be '{settings.AUTH_USER_PATH}'."
        )
    invalid_chars = re.findall(r'^[\\w.@+-]+\\z', username)
    if invalid_chars:
        raise ValidationError(
            f"Username contains invalid characters:"
            f" {''.join(set(invalid_chars))}"
        )


def validate_slug(slug):
    invalid_chars = re.findall(r'^[-a-zA-Z0-9_]+$', slug)
    if invalid_chars:
        raise ValidationError(
            f"Slug contains invalid characters:"
            f" {''.join(set(invalid_chars))}"
        )
