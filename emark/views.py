from urllib.parse import urlparse

from django import http
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http.request import split_domain_port, validate_host
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin

from . import models
from .registry import registry

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


class EmailDataMixin:
    def get_email_data(self, email_class):
        return {
            "app_label": email_class.__module__.split(".")[0],
            "class": email_class,
            "name": email_class.__name__,
            "doc": email_class.__doc__ or "",
            "detail_url": reverse_lazy(
                "emark:email-preview", args=[email_class.__name__]
            ),
            "preview": email_class.render_preview(),
        }


class DashboardView(LoginRequiredMixin, EmailDataMixin, TemplateView):
    """Show a dashboard of available email classes."""

    template_name = "emark/dashboard.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "emails": [
                self.get_email_data(email_data["cls"])
                for email_data in registry.values()
            ],
        }


class EmailPreviewView(LoginRequiredMixin, EmailDataMixin, TemplateView):
    """Render a preview of the email."""

    template_name = "emark/preview.html"

    def dispatch(self, request, *args, **kwargs):
        self.email_class = registry.get(kwargs["email_class"])
        if not self.email_class:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "email": self.get_email_data(self.email_class["cls"]),
        }
