from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EmarkConfig(AppConfig):
    name = "emark"
    verbose_name = _("emark")
    emails = []
