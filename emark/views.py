from urllib.parse import urlparse

from django import http
from django.conf import settings
from django.http.request import split_domain_port, validate_host
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from . import models

# white 1x1 pixel JPEG in bytes:
#
# import io
# from PIL import Image
#
# img = Image.new('RGB', (1, 1), color='white')
# img_bytes = io.BytesIO()
# img.save(img_bytes, format='GIF')
# TRACKING_PIXEL_GIF = img_bytes.getvalue()
TRACKING_PIXEL_GIF = b"GIF87a\x01\x00\x01\x00\x81\x00\x00\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x08\x04\x00\x01\x04\x04\x00;"


class EmailDetailView(SingleObjectMixin, View):
    """Return the HTML body of the email."""

    model = models.Send

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.html:
            return http.HttpResponse(
                self.object.html.encode(), status=200, content_type="text/html"
            )
        return http.HttpResponse(
            self.object.body.encode(), status=200, content_type="text/plain"
        )


class EmailClickView(SingleObjectMixin, View):
    """Redirect to the URL and track the click."""

    model = models.Send

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        redirect_to = request.GET.get("url")
        # The redirect_to URL is user-provided, so it might be malicious
        # or malformed. We use Django's URL validation to ensure that it
        # is safe to redirect to.
        parsed_url = urlparse(redirect_to)
        if not parsed_url.netloc:
            return http.HttpResponseBadRequest("Missing url or malformed parameter")

        domain, _port = split_domain_port(parsed_url.netloc)
        allowed_hosts = settings.ALLOWED_HOSTS
        if settings.DEBUG:
            allowed_hosts = settings.ALLOWED_HOSTS + [
                ".localhost",
                "127.0.0.1",
                "[::1]",
            ]
        if any(
            [
                not domain,
                not validate_host(domain, allowed_hosts),
                request.scheme != parsed_url.scheme,
            ]
        ):
            return http.HttpResponseBadRequest("Missing url or malformed parameter")

        models.Click.objects.create_for_request(
            request, email=self.object, redirect_url=redirect_to
        )
        return http.HttpResponseRedirect(redirect_to)


class EmailOpenView(SingleObjectMixin, View):
    """Return a tracking pixel and track the open."""

    model = models.Send

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        models.Open.objects.create_for_request(request, email=self.object)

        return http.HttpResponse(
            TRACKING_PIXEL_GIF,
            status=200,
            content_type="image/gif",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
