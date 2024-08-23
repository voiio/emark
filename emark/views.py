from urllib.parse import urlparse

from django import http
from django.apps import apps
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http.request import split_domain_port, validate_host
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
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


class DashboardView(LoginRequiredMixin, TemplateView):
    """Show a dashboard of available email classes."""

    template_name = "emark/dashboard.html"

    def get_emails(self):
        emails = [
            {
                "app_label": email_class.__module__.split(".")[0],
                "class_name": email_class.__name__,
                "doc": email_class.__doc__ or "",
                "detail_url": reverse(
                    "emark:email-preview", args=[email_class.__name__]
                ),
            }
            for email_class in apps.get_app_config("emark").emails
        ]
        return sorted(
            emails, key=lambda email: (email["app_label"], email["class_name"])
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "emails": self.get_emails(),
        }


class EmailPreviewView(LoginRequiredMixin, TemplateView):
    """Render a preview of the email."""

    template_name = "emark/preview.html"

    def dispatch(self, request, *args, **kwargs):
        self.email_class = self.get_email_class(kwargs["email_class"])
        if not self.email_class:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_email_class(self, email_class):
        return next(
            (
                email
                for email in apps.get_app_config("emark").emails
                if email.__name__ == email_class
            ),
            None,
        )

    def get_context_data(self, **kwargs):
        email = self.email_class
        return super().get_context_data(**kwargs) | {
            "email": {
                "name": email.__name__,
                "doc": email.__doc__,
                "preview": email.render_preview(),
            }
        }
