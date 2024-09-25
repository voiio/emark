from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from ...message import MarkdownEmail
from . import _registry


def serialize_email_class(email_class: type[MarkdownEmail], path: str) -> {str: str}:
    return {
        "app_label": email_class.__module__.split(".")[0],
        "class": email_class,
        "name": email_class.__name__,
        "doc": email_class.__doc__ or "",
        "detail_url": reverse("emark-dashboard:email-preview", args=[path]),
        "preview": email_class.render_preview,
    }


class DashboardView(TemplateView):
    """Show a dashboard of available email classes."""

    template_name = "emark/dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "site_header": "eMark",
            "site_title": "eMark",
            "title": "Dashboard",
            "emails": [
                serialize_email_class(klass, path) for path, klass in _registry.items()
            ],
        }


class EmailPreviewView(TemplateView):
    """Render a preview of the email."""

    template_name = "emark/dashboard/preview.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.email_class = _registry[kwargs["email_class"]]
        except KeyError as e:
            raise Http404() from e
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "site_header": "eMark",
            "site_title": "eMark",
            "title": "Dashboard",
            "subtitle": self.email_class.__name__,
            "email": serialize_email_class(
                self.email_class, self.kwargs["email_class"]
            ),
        }
