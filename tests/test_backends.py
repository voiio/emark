import io
import smtplib
from unittest.mock import MagicMock, Mock

import pytest
from django.core.mail import EmailMultiAlternatives

from emark import backends
from emark.models import Send


class TestConsoleEmailBackend:
    def test_write_message(self):
        msg = EmailMultiAlternatives(body="foo")
        msg.attach_alternative("<html></html>", "text/html")
        with io.StringIO() as stream:
            backends.ConsoleEmailBackend(stream=stream).write_message(msg)
            stdout = stream.getvalue()
            assert "html" not in stdout
            assert "1 more attachment(s) have been omitted." in stdout


class TestTrackingConsoleEmailBackend:
    @pytest.mark.django_db
    def test_send(self, email_message):
        email_message.to = [
            "peter.parker@avengers.com",
            "dr.strange@avengers.com",
        ]
        email_message.cc = ["t-dog@avengers.com"]

        with io.StringIO() as stream:
            backend = backends.TrackingConsoleEmailBackend(stream=stream)
            assert backend.send_messages([email_message]) == 1
        assert Send.objects.count() == 3
        obj = Send.objects.get(to_address="peter.parker@avengers.com")
        assert str(obj.uuid) in obj.body

    @pytest.mark.django_db
    def test_send__with_user(self, admin_user, email_message):
        email_message.to = [admin_user.email]
        email_message.user = admin_user

        with io.StringIO() as stream:
            backend = backends.TrackingConsoleEmailBackend(stream=stream)
            assert backend.send_messages([email_message]) == 1

        assert Send.objects.count() == 1
        obj = Send.objects.get(to_address=admin_user.email)
        assert obj.user == admin_user

    @pytest.mark.django_db
    def test_write_message__native_email(self):
        msg = EmailMultiAlternatives(to=["ironman@avengers.com"], body="foo")
        msg.attach_alternative("<html></html>", "text/html")
        with io.StringIO() as stream:
            backends.TrackingConsoleEmailBackend(stream=stream).send_messages([msg])
            stdout = stream.getvalue()
            assert "html" not in stdout
            assert "1 more attachment(s) have been omitted." in stdout
        assert Send.objects.count() == 1

    @pytest.mark.django_db
    def test_write_message__native_email__multiple_receipients(self):
        msg = EmailMultiAlternatives(
            to=["spiderman@avengers.com"], cc=["peter.parker@aol.com"], body="foo"
        )
        msg.attach_alternative("<html></html>", "text/html")
        with io.StringIO() as stream:
            backends.TrackingConsoleEmailBackend(stream=stream).send_messages([msg])
            stdout = stream.getvalue()
            assert "To: peter.parker@aol.com" in stdout
            assert "To: spiderman@avengers.com" in stdout
            assert "Cc:" not in stdout
        assert Send.objects.count() == 2


class TestTrackingSMTPEmailBackend:
    @pytest.mark.django_db
    def test_send(self, email_message):
        email_message.to = [
            "peter.parker@avengers.com",
            "dr.strange@avengers.com",
        ]
        email_message.cc = ["t-dog@avengers.com"]

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=False)
        backend.connection = Mock()
        assert backend.send_messages([email_message]) == 1
        assert backend.connection.sendmail.call_count == 3
        assert Send.objects.count() == 3
        obj = Send.objects.get(to_address="peter.parker@avengers.com")
        assert str(obj.uuid) in obj.body

    @pytest.mark.django_db
    def test_send__native_email(self):
        email_message = EmailMultiAlternatives(
            to=[
                "peter.parker@avengers.com",
                "dr.strange@avengers.com",
            ],
            cc=["t-dog@avengers.com"],
            body="foo",
        )

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=False)
        backend.connection = Mock()
        assert backend.send_messages([email_message]) == 1
        assert backend.connection.sendmail.call_count == 3
        assert Send.objects.count() == 3

    @pytest.mark.django_db
    def test_send__with_user(self, admin_user, email_message):
        email_message.to = [admin_user.email]
        email_message.user = admin_user

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=False)
        backend.connection = Mock()
        assert backend.send_messages([email_message]) == 1
        assert backend.connection.sendmail.call_count == 1
        assert Send.objects.count() == 1
        obj = Send.objects.get(to_address=admin_user.email)
        assert obj.user == admin_user

    @pytest.mark.django_db
    def test_send__smtp_error(self, email_message):
        email_message.to = [
            "peter.parker@avengers.com",
            "dr.strange@avengers.com",
        ]
        email_message.cc = ["t-dog@avengers.com"]

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=False)
        backend.connection = Mock()
        backend.connection.sendmail.side_effect = smtplib.SMTPException
        with pytest.raises(smtplib.SMTPException):
            backend.send_messages([email_message])
        assert backend.connection.sendmail.call_count == 1
        assert not Send.objects.exists()

    @pytest.mark.django_db
    def test_send__fail_silently_wo_error(self, email_message):
        email_message.to = [
            "peter.parker@avengers.com",
            "dr.strange@avengers.com",
        ]
        email_message.cc = ["t-dog@avengers.com"]

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=True)
        backend.connection = Mock()
        assert backend.send_messages([email_message]) == 1
        assert backend.connection.sendmail.call_count == 3
        assert Send.objects.count() == 3
        obj = Send.objects.get(to_address="peter.parker@avengers.com")
        assert str(obj.uuid) in obj.body

    @pytest.mark.django_db
    def test_send__fail_silently_w_error(self, email_message):
        email_message.to = [
            "peter.parker@avengers.com",
            "dr.strange@avengers.com",
        ]
        email_message.cc = ["t-dog@avengers.com"]

        class TestBackend(backends.TrackingSMTPEmailBackend):
            connection_class = MagicMock

        backend = TestBackend(fail_silently=True)
        backend.connection = Mock()
        backend.connection.sendmail.side_effect = smtplib.SMTPException
        assert backend.send_messages([email_message]) == 0
        assert backend.connection.sendmail.call_count == 1
        assert not Send.objects.exists()
