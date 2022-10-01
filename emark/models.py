from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailStatistic(models.Model):
    amount_sent = models.PositiveSmallIntegerField(_("amount sent"))
    utm_campaign = models.CharField(
        _("utm campaign name"),
        max_length=255,
        help_text=_("UTM campaign name matches the email class name."),
        db_index=True,
    )
    modified = models.DateTimeField(
        _("modified"),
        auto_now=True,
        editable=False,
        db_index=True,
    )
    created = models.DateTimeField(
        _("created"),
        auto_now_add=True,
        editable=False,
        db_index=True,
    )

    class Meta:
        ordering = ("-modified", "-created")
        get_latest_by = "created"


class LanguageUserMixin(models.Model):
    """Provide a language field for a Django user."""

    language = models.TextField(_("language"), choices=settings.LANGUAGES, default="")

    class Meta:
        abstract = True
