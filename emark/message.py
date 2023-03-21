from __future__ import annotations

import logging
import re
from urllib import parse

import markdown
import premailer
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils import translation
from django.utils.safestring import mark_safe

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
        template = template or self.get_template()
        self.context = context or {}
        self.language = language
        utm_params = utm_params or {}

        context = self.get_context_data(**self.context)
        context |= self.get_utm_params(**utm_params)

        with translation.override(language):
            subject = subject or self.get_subject(**context)
            markdown_string = self.get_markdown_string(template, context, utm_params)

            self.html = self.render_html(
                markdown_string=markdown_string,
                context={
                    "subject": subject,
                    **context,
                },
            )

            parser = utils.HTML2TextParser()
            parser.feed(self.html)
            lines = str(parser).split("\n")
            body = "\n".join(lines[1:]).strip()  # remove logo
            super().__init__(subject=subject, body=body, **kwargs)
            self.attach_alternative(self.html, "text/html")

    @classmethod
    def get_utm_params(cls, **params: {str: str}) -> {str: str}:
        """Return a dictionary of UTM parameters."""
        return (
            conf.get_settings().UTM_PARAMS
            | {
                "utm_campaign": cls.get_utm_campaign_name(),
            }
            | params
        )

    @classmethod
    def get_utm_campaign_name(cls):
        """Return the UTM campaign name for this email."""
        return "_".join(
            (m.group(0) for m in CLS_NAME_TO_CAMPAIGN_RE.finditer(cls.__qualname__))
        ).upper()

    @staticmethod
    def update_url_params(url, **params):
        url_parse = parse.urlparse(url)
        url_params = dict(parse.parse_qsl(url_parse.query))
        params.update(url_params)
        url_new_query = parse.urlencode(params)
        url_parse = url_parse._replace(query=url_new_query)
        return parse.urlunparse(url_parse)

    @classmethod
    def set_utm_attributes(cls, md, **utm):
        for url in INLINE_LINK_RE.findall(md):
            md = md.replace(f"({url})", f"({cls.update_url_params(url, **utm)})")
        for url in INLINE_HTML_LINK_RE.findall(md):
            md = md.replace(
                f'href="{url}"', f'href="{cls.update_url_params(url, **utm)}"'
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
        return cls(
            **{
                "to": [f'"{user.get_full_name()}" <{user.email}>'],
                "context": context,
                "language": language,
            }
            | kwargs
        )

    def get_template(self):
        if not self.template:
            raise ImproperlyConfigured(
                f"{self.__class__.__qualname__} is missing a template."
            )
        return self.template

    def get_context_data(self, **context):
        """Return the context data for the email."""
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
        markdown_string = self.set_utm_attributes(
            markdown_string, **self.get_utm_params(**utm)
        )
        return markdown_string

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
