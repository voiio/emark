import copy
import smtplib
import uuid

from django.conf import settings
from django.core.mail.backends.console import EmailBackend as _EmailBackend
from django.core.mail.backends.smtp import EmailBackend as _SMTPEmailBackend
from django.core.mail.message import sanitize_address

from emark import models
from emark.message import MarkdownEmail

__all__ = [
    "ConsoleEmailBackend",
    "TrackingConsoleEmailBackend",
    "TrackingSMTPEmailBackend",
]


class TrackingEmailBackendMixin:
    """Add tracking framework to an email backend."""

    def send_messages(self, email_messages):
        self._messages_sent = []
        try:
            return super().send_messages(email_messages)
        finally:
            models.Send.objects.bulk_create(self._messages_sent)

    def _track_message_clone(self, clone, message):
        if isinstance(clone, MarkdownEmail):
            self._messages_sent.append(
                models.Send(
                    pk=clone._tracking_uuid,
                    from_address=message["From"],
                    to_address=message["To"],
                    subject=message["Subject"],
                    body=clone.body,
                    html=clone.html,
                    user=getattr(clone, "user", None),
                    utm=clone.get_utm_params(**clone.utm_params),
                )
            )
        else:
            self._messages_sent.append(
                models.Send(
                    pk=clone._tracking_uuid,
                    from_address=message["From"],
                    to_address=message["To"],
                    subject=message["Subject"],
                    body=clone.body,
                )
            )


class ConsoleEmailBackend(_EmailBackend):
    """Like the console email backend but only with the plain text body."""

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


class TrackingConsoleEmailBackend(TrackingEmailBackendMixin, ConsoleEmailBackend):
    """Like the console email backend but with click and open tracking."""

    def write_message(self, message):
        for recipient in message.recipients():
            clone = copy.copy(message)
            clone.to = [recipient]
            clone.cc = []
            clone.bcc = []
            # enable tracking
            clone._tracking_uuid = uuid.uuid4()
            msg = super().write_message(clone)
            self._track_message_clone(clone, msg)


class TrackingSMTPEmailBackend(TrackingEmailBackendMixin, _SMTPEmailBackend):
    """
    Like the SMTP email backend but with click and open tracking.

    Furthermore, all emails are sent to a single email address.
    If multiple to, cc, or bcc addresses are specified, a separate
    email is sent individually to each address.
    """

    def _send(self, email_message):
        for recipient in email_message.recipients():
            clone = copy.copy(email_message)
            clone.to = [recipient]
            clone.cc = []
            clone.bcc = []
            # enable tracking
            clone._tracking_uuid = uuid.uuid4()

            encoding = clone.encoding or settings.DEFAULT_CHARSET
            from_email = sanitize_address(clone.from_email, encoding)
            recipients = [sanitize_address(recipient, encoding)]
            message = clone.message()
            try:
                self.connection.sendmail(
                    from_email, recipients, message.as_bytes(linesep="\r\n")
                )
            except smtplib.SMTPException:
                if not self.fail_silently:
                    raise
                return False
            else:
                self._track_message_clone(clone, message)
        return True
