import copy
import smtplib
import uuid

from django.conf import settings
from django.core.mail.backends.console import EmailBackend as _EmailBackend
from django.core.mail.backends.smtp import EmailBackend as _SMTPEmailBackend
from django.core.mail.message import sanitize_address

from emark import models

__all__ = ["ConsoleEmailBackend", "TrackingSMTPEmailBackend"]


class ConsoleEmailBackend(_EmailBackend):
    """Like the console email backend but only with the plain text body."""

    def write_message(self, message):
        setattr(message, "alternatives", [])
        return super().write_message(message)


class TrackingSMTPEmailBackend(_SMTPEmailBackend):
    """
    Like the SMTP email backend but with click and open tracking.

    Furthermore, all emails are sent to a single email address.
    If multiple to, cc, or bcc addresses are specified, a separate
    email is sent individually to each address.
    """


    def _send(self, email_message):
        for recipient in email_message.recipients():
            clone = copy.deepcopy(email_message)
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
                models.Send.objects.create(
                    pk=clone._tracking_uuid,
                    from_address=from_email,
                    to_address=recipient,
                    subject=message["Subject"],
                    body=clone.body,
                    html=clone.html,
                    utm=clone.get_utm_params(**clone.utm_params),
                )
        return True
