from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class TestUser(AbstractUser):
    language = models.TextField(
        _("language"), choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
