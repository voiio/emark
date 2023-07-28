import uuid

from django.core.mail import EmailMessage
from django.core.mail.backends.console import EmailBackend as _EmailBackend
from django.core.mail.backends.smtp import EmailBackend as _SMTPEmailBackend

from emark import models
from emark.message import MarkdownEmail

__all__ = [
    "ConsoleEmailBackend",
    "SMTPEmailBackend",
    "TrackingConsoleEmailBackend",
    "TrackingSMTPEmailBackend",
]


class RenderEmailBackendMixin:
    def send_messages(self, email_messages):
        for message in email_messages:
            if isinstance(message, MarkdownEmail):
                message.render()
        return super().send_messages(email_messages)


class TrackingEmailBackendMixin:
    """Add tracking framework to an email backend."""

    def send_messages(self, email_messages):
        self._messages_sent = []
        for message in email_messages:
            if isinstance(message, MarkdownEmail):
                message.render(tracking_uuid=uuid.uuid4())
        try:
            return super().send_messages(email_messages)
        finally:
            models.Send.objects.bulk_create(self._messages_sent)

    def _track_message(self, message: EmailMessage):
        if isinstance(message, MarkdownEmail):
            self._messages_sent.append(
                models.Send(
                    pk=message.uuid,
                    from_email=message.from_email,
                    to=message.to,
                    cc=message.cc,
                    bcc=message.bcc,
                    reply_to=message.reply_to,
                    subject=message.subject,
                    body=message.body,
                    html=message.html,
                    user=getattr(message, "user", None),
                    utm=message.get_utm_params(),
                )
            )
        else:
            self._messages_sent.append(
                models.Send(
                    from_email=message.from_email,
                    to=message.to,
                    cc=message.cc,
                    bcc=message.bcc,
                    reply_to=message.reply_to,
                    subject=message.subject,
                    body=message.body,
                )
            )


class ConsoleEmailBackendMixin:
    """Drop email alternative parts and attachments for the console backend."""

    def write_message(self, message):
        msg = message.message()
        payload_count = len(msg.get_payload())
        msg.set_payload(msg.get_payload(0))
        msg_data = msg.as_bytes()
        charset = (
            msg.get_charset().get_output_charset() if msg.get_charset() else "utf-8"
        )
        msg_data = msg_data.decode(charset)
        self.stream.write("%s\n" % msg_data)
        self.stream.write("-" * 79)
        self.stream.write("\n")
        if payload_count > 1:
            self.stream.write(
                f"{payload_count - 1} more attachment(s) have been omitted.\n"
            )

        return msg


class ConsoleEmailBackend(
    RenderEmailBackendMixin, ConsoleEmailBackendMixin, _EmailBackend
):
    """Like the console email backend but only with the plain text body."""


class SMTPEmailBackend(RenderEmailBackendMixin, _SMTPEmailBackend):
    """SMTP email backend that renders messages before establishing an SMTP transport."""

    pass


class TrackingConsoleEmailBackend(
    TrackingEmailBackendMixin, ConsoleEmailBackendMixin, _EmailBackend
):
    """Like the console email backend but with click and open tracking."""

    def write_message(self, message):
        try:
            return super().write_message(message)
        finally:
            self._track_message(message)


class TrackingSMTPEmailBackend(TrackingEmailBackendMixin, _SMTPEmailBackend):
    """
    Like the SMTP email backend but with click and open tracking.

    Furthermore, all emails are sent to a single email address.
    If multiple to, cc, or bcc addresses are specified, a separate
    email is sent individually to each address.
    """

    def _send(self, email_message):
        sent = False
        try:
            sent = super()._send(email_message)
            return sent
        finally:
            if sent:
                self._track_message(email_message)
