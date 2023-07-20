from __future__ import annotations

import logging
import re
from urllib import parse

import markdown
import premailer
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.urls import reverse
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext

from emark import conf, utils

INLINE_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_HTML_LINK_RE = re.compile(r"href=\"([^\"]+)\"")
CLS_NAME_TO_CAMPAIGN_RE = re.compile(
    r".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)"
)


class MarkdownEmail(EmailMultiAlternatives):
    """
    Multipart email message that renders both plaintext and HTML from markdown.

    This is a full class:`EmailMultiAlternatives` subclass with additional support
    to send emails directly to a users. It also requires an explicit language
    (if not provided by the user) to ensure the correct language is used.

    Markdown templates are rendered using Django's template engine. The markdown
    may contain HTML tags. The HTML tags are rendered as-is, except for the plain
    text body, which extracts a Gmail style plain text version of the fully rendered
    HTML email.
    """

    base_html_template = "emark/base.html"
    template = None
    subject = None
    _tracking_uuid = False

    def __init__(
        self,
        language: str,
        subject: str = "",
        context: dict = None,
        utm_params=None,
        template=None,
        **kwargs,
    ):
        """Initialize an email message and attach a rendered HTML version of it."""
        self.template = template or self.template
        self.context = context or {}
        self.language = language
        self.utm_params = utm_params or {}
        self.subject = subject or self.subject
        super().__init__(subject=self.subject, **kwargs)

    def get_html(self):
        """Return the rendered HTML version of the email."""
        with translation.override(self.language):
            utm_params = self.get_utm_params()
            context = self.get_context_data(**utm_params)
            context |= utm_params
            template = self.get_template()
            subject = self.get_subject(**context)

            markdown_string = self.get_markdown_string(template, context, utm_params)

            return self.render_html(
                markdown_string=markdown_string,
                context={
                    "subject": subject,
                    **context,
                },
            )

    def get_body(self, html):
        """Return the parsed plain text version of the rendered HTML email."""
        parser = utils.HTML2TextParser()
        parser.feed(html)
        parser.close()
        body = str(parser)
        if self._tracking_uuid:
            href = reverse("emark:email-detail", kwargs={"pk": self._tracking_uuid})
            href = parse.urljoin(self.get_site_url(), href)
            txt = capfirst(gettext("view in browser"))
            body = f"{txt} <{href}>\n\n" + body
        return body

    def message(self):
        # The connection will call .message while sending the email.
        self.subject = self.get_subject(**self.get_context_data())
        self.html = self.get_html()
        self.body = self.get_body(self.html)
        self.attach_alternative(self.html, "text/html")
        return super().message()

    def get_utm_params(self, **params: {str: str}) -> {str: str}:
        """Return a dictionary of UTM parameters."""
        return (
            conf.get_settings().UTM_PARAMS
            | {
                "utm_campaign": self.get_utm_campaign_name(),
            }
            | self.utm_params
            | params
        )

    @classmethod
    def get_utm_campaign_name(cls):
        """Return the UTM campaign name for this email."""
        return "_".join(
            (m.group(0) for m in CLS_NAME_TO_CAMPAIGN_RE.finditer(cls.__qualname__))
        ).upper()

    def update_url_params(self, url, **params):
        """Add UTM parameters to a URL and add the click tracking URL."""
        redirect_url_parts = parse.urlparse(url)
        url_params = dict(parse.parse_qsl(redirect_url_parts.query))
        params.update(url_params)
        url_new_query = parse.urlencode(params)
        redirect_url_parts = redirect_url_parts._replace(query=url_new_query)
        redirect_url = parse.urlunparse(redirect_url_parts)
        if not self._tracking_uuid:
            return redirect_url
        tracking_url = reverse("emark:email-click", kwargs={"pk": self._tracking_uuid})
        tracking_url = parse.urljoin(self.get_site_url(), tracking_url)
        tracking_url_parts = parse.urlparse(tracking_url)
        tracking_url_parts = tracking_url_parts._replace(
            query=parse.urlencode({"url": redirect_url})
        )
        return parse.urlunparse(tracking_url_parts)

    def set_utm_attributes(self, md, **utm):
        for url in INLINE_LINK_RE.findall(md):
            md = md.replace(f"({url})", f"({self.update_url_params(url, **utm)})")
        for url in INLINE_HTML_LINK_RE.findall(md):
            md = md.replace(
                f'href="{url}"', f'href="{self.update_url_params(url, **utm)}"'
            )
        return md

    @classmethod
    def to_user(cls, user=None, context=None, language=None, **kwargs):
        """Return email with user specific language, context and recipient."""
        if not user.email:
            raise ValueError("User has no email address")
        if not user.is_active:
            raise ValueError("User is not active")
        if settings.USE_I18N:
            try:
                language = language or user.language
            except AttributeError as e:
                raise ValueError(
                    "If your user model does not have a language field,"
                    " you must provide a language."
                ) from e
        context = context or {}
        context |= {
            "short_name": user.get_short_name(),
            "user": user,
        }
        obj = cls(
            **{
                "to": [f'"{user.get_full_name()}" <{user.email}>'],
                "context": context,
                "language": language,
            }
            | kwargs
        )
        obj.user = user
        return obj

    def get_template(self):
        if not self.template:
            raise ImproperlyConfigured(
                f"{self.__class__.__qualname__} is missing a template."
            )
        return self.template

    def get_site_url(self):
        protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
        if domain := conf.get_settings().DOMAIN:
            pass
        elif apps.is_installed("django.contrib.sites"):
            from django.contrib.sites.models import Site

            domain = Site.objects.get_current().domain

        return parse.urlunparse((protocol, domain, "", "", "", ""))

    def get_context_data(self, **context):
        """Return the context data for the email."""
        if self._tracking_uuid:
            context |= {
                "tracking_uuid": self._tracking_uuid,
                "view_in_browser_url": parse.urljoin(
                    self.get_site_url(),
                    reverse("emark:email-detail", kwargs={"pk": self._tracking_uuid}),
                ),
                "tracking_pixel_url": parse.urljoin(
                    self.get_site_url(),
                    reverse("emark:email-open", kwargs={"pk": self._tracking_uuid}),
                ),
            }

        return self.context | context

    def get_subject(self, **context):
        """Return the email's subject."""
        if not self.subject:
            raise ImproperlyConfigured(
                f"{self.__class__.__qualname__} is missing a subject."
            )
        return self.subject

    def get_markdown_string(self, template, context, utm):
        markdown_string = loader.get_template(template).render(context)
        return self.set_utm_attributes(markdown_string, **self.get_utm_params(**utm))

    def render_html(self, markdown_string, context):
        html_message = markdown.markdown(
            markdown_string,
            extensions=[
                "markdown.extensions.meta",
                "markdown.extensions.tables",
                "markdown.extensions.extra",
            ],
        )
        context["markdown_string"] = mark_safe(html_message)  # nosec

        template = loader.get_template(self.base_html_template)
        rendered_html = template.render(context)

        inlined_html = premailer.transform(
            html=rendered_html,
            strip_important=False,
            keep_style_tags=True,
            cssutils_logging_level=logging.WARNING,
        )
        return inlined_html
