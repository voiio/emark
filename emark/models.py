import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Send(models.Model):
    """Frozen replica of a sent email message."""

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False, primary_key=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="emark_emails",
        null=True,
    )
    from_address = models.EmailField()
    to_address = models.EmailField()
    subject = models.TextField(max_length=998)  # RFC 2822
    body = models.TextField()
    html = models.TextField(null=True)
    utm = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return reverse("emark:email-detail", kwargs={"pk": self.pk})


class ClientTrackingQueryset(models.QuerySet):
    def create_for_request(self, request, **kwargs):
        """Create a tracking record for the given request."""
        return self.create(
            headers=dict(request.headers),
            ip_address=request.META.get("REMOTE_ADDR"),
            utm={
                key: value
                for key, value in request.GET.items()
                if key.startswith("utm_")
            },
            **kwargs,
        )


class ClientTrackingModelMixin(models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False, primary_key=True
    )
    headers = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    utm = models.JSONField(default=dict)

    objects = ClientTrackingQueryset.as_manager()

    class Meta:
        abstract = True


class Click(ClientTrackingModelMixin):
    """Record of a click on a link in an email."""

    email = models.ForeignKey(Send, on_delete=models.CASCADE)
    # we don't need validation here, but we do need to store long URLs
    redirect_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Open(ClientTrackingModelMixin):
    """Record of an email being opened."""

    email = models.ForeignKey(Send, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
