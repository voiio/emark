from django.contrib.auth.models import AbstractUser

from emark.models import LanguageUserMixin


class TestUser(LanguageUserMixin, AbstractUser):
    pass
