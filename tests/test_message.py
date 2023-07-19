import copy
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test.html import parse_html
from model_bakery import baker

import emark.message

BASE_DIR = Path(__file__).resolve().parent.parent


class MarkdownEmailTest(emark.message.MarkdownEmail):
    template = "template.md"


class MarkdownEmailTestWithSubject(MarkdownEmailTest):
    subject = "Which Donut Are You?"


class TestMarkdownEmail:
    @pytest.fixture(autouse=True)
    def _add_test_template(self, settings):
        overloaded_template = settings.TEMPLATES.copy()
        overloaded_template[0]["DIRS"] = [BASE_DIR / "tests/templates"]
        settings.TEMPLATES = overloaded_template

    def test_to_user(self):
        user = baker.prepare(
            settings.AUTH_USER_MODEL,
            first_name="Peter",
            last_name="Parker",
            email="spiderman@avengers.com",
            language="fr",
        )
        email = MarkdownEmailTest.to_user(
            user,
            subject="I don't want to go!",
            context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
        )
        assert email.to == ['"Peter Parker" <spiderman@avengers.com>']
        assert email.context == {
            "user": user,
            "donut_name": "Nutty Donut",
            "donut_type": "Frosted",
            "short_name": "Peter",
        }
        assert email.language == "fr"
        assert email.user == user

    def test_to_user__no_email(self):
        user = baker.prepare(
            settings.AUTH_USER_MODEL,
            email="",
        )
        with pytest.raises(ValueError) as e:
            MarkdownEmailTest.to_user(
                user,
                subject="I don't want to go!",
                context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
            )
        assert str(e.value) == "User has no email address"

    def test_to_user__inactive_user(self):
        user = baker.prepare(
            settings.AUTH_USER_MODEL,
            email="spiderman@avengers.com",
            is_active=False,
        )
        with pytest.raises(ValueError) as e:
            MarkdownEmailTest.to_user(
                user,
                subject="I don't want to go!",
                context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
            )
        assert str(e.value) == "User is not active"

    @pytest.mark.django_db
    def test_to_user__no_language(self):
        user = baker.prepare(
            "auth.User",
            email="spiderman@avengers.com",
        )
        with pytest.raises(ValueError) as e:
            MarkdownEmailTest.to_user(
                user,
                subject="I don't want to go!",
                context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
            )
        assert (
            str(e.value)
            == "If your user model does not have a language field, you must provide a language."
        )

    @pytest.mark.django_db
    def test_to_user__i18n_off(self, settings):
        settings.USE_I18N = False
        user = baker.prepare(
            "auth.User",
            email="spiderman@avengers.com",
        )
        MarkdownEmailTest.to_user(
            user,
            subject="I don't want to go!",
            context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
        ).send()

    def test_to_user__override_default(self):
        user = baker.prepare(
            settings.AUTH_USER_MODEL,
            first_name="Peter",
            last_name="Parker",
            email="spiderman@avengers.com",
            language="fr",
        )
        email = MarkdownEmailTest.to_user(
            user,
            to=['"Tony Stark" <ironman@avengers.com>'],
            subject="I don't want to go!",
            context={"donut_name": "Nutty Donut", "donut_type": "Frosted"},
        )
        assert email.to == ['"Tony Stark" <ironman@avengers.com>']

    def test_email(self, email_message):
        email_message.message()
        assert email_message.subject == "Peanut strikes back"

        assert (
            parse_html(
                """
        <h1 style="color:#000; font-family:sans-serif; font-weight:300; line-height:1.4; margin:0; margin-bottom:30px; font-size:35px; text-align:center; text-transform:capitalize" align="center">
            Nutty Donut
        </h1>
        <h2 style="color:#000; font-family:sans-serif; font-weight:400; line-height:1.4; margin:0; margin-bottom:30px">
            Description
        </h2>
        <p style="font-family:sans-serif; font-size:14px; font-weight:normal; margin:0; margin-bottom:15px">
            <em>Type: Frosted</em>
        </p>
        <p style="font-family:sans-serif; font-size:14px; font-weight:normal; margin:0; margin-bottom:15px">
            Vanilla lollipop biscuit cake marzipan jelly.
        </p>
                """
            )
            in parse_html(email_message.html)
        )

        assert len(email_message.alternatives) == 1

        alternative_html, alternative_type = email_message.alternatives[0]

        assert alternative_type == "text/html"
        assert alternative_html == email_message.html

    def test_send(self, email_message, mailoutbox):
        email_message.send()

        assert len(mailoutbox) == 1
        received_email = mailoutbox[0]
        assert received_email.to == ["test@example.com"]
        assert received_email.from_email == "webmaster@localhost"
        assert received_email.subject == "Peanut strikes back"

        assert received_email.alternatives

    def test_body(self, email_message):
        email_message.message()
        message_text = (
            "Description\n\n*Type: Frosted*\n\nVanilla lollipop "
            "biscuit cake marzipan jelly.\n\n"
        )
        assert message_text in email_message.body

    def test_open_tracking(self, email_message):
        email_message._tracking_uuid = "12341234-1234-1234-1234-123412341234"
        email_message.message()
        assert (
            'background-image: url("http://www.example.com/emark/12341234-1234-1234-1234-123412341234/open")'
            in email_message.html
        )

    def test_open_in_browser__body(self, email_message):
        email_message._tracking_uuid = "12341234-1234-1234-1234-123412341234"
        email_message.message()
        assert (
            "View in browser <http://www.example.com/emark/12341234-1234-1234-1234-123412341234/>"
            in email_message.body
        )

    def test_open_in_browser__html(self, email_message):
        email_message._tracking_uuid = "12341234-1234-1234-1234-123412341234"
        email_message.message()
        assert (
            '<a class="open-in-browser" href="http://www.example.com/emark/12341234-1234-1234-1234-123412341234/" style="color:#3498db; text-decoration:underline; text-align:right" align="right">'
            in email_message.html
        )

    def test_get_site_domain__setting(self, email_message):
        assert email_message.get_site_url() == "http://www.example.com"

    @pytest.mark.django_db
    def test_test_get_site_domain__sites_framework(self, email_message, settings):
        settings.EMARK = {"DOMAIN": None}
        settings.SITE_ID = 1
        assert email_message.get_site_url() == "http://example.com"

    def test_custom_context(self):
        custom_context = {"donut_name": "HoneyNuts", "donut_type": "Honey"}
        email_message = MarkdownEmailTest(
            language="en-US",
            subject="Peanut strikes back",
            context=custom_context,
        )
        assert email_message.get_context_data(**custom_context) == {
            "donut_type": "Honey",
            "donut_name": "HoneyNuts",
        }

    def test_get_template(self):
        msg = emark.message.MarkdownEmail(
            language="en-US",
            subject="Peanut strikes back",
        )
        with pytest.raises(ImproperlyConfigured):
            msg.message()

    def test_get_subject__missing(self):
        msg = emark.message.MarkdownEmail(
            template="template.md",
            language="en-US",
            context={"donut_name": "HoneyNuts", "donut_type": "Honey"},
        )
        with pytest.raises(ImproperlyConfigured) as e:
            msg.message()
        assert str(e.value) == "MarkdownEmail is missing a subject."

    def test_get_subject(self):
        email_message = MarkdownEmailTestWithSubject(
            language="en-US",
            context={"donut_name": "HoneyNuts", "donut_type": "Honey"},
        )
        assert email_message.subject == "Which Donut Are You?"

    def test_set_utm_attributes(self):
        email_message = MarkdownEmailTestWithSubject(
            language="en-US",
            context={"donut_name": "HoneyNuts", "donut_type": "Honey"},
        )
        email_message.message()
        assert (
            "This is a link! <https://www.example.com?utm_source=website&utm_medium=email&utm_campaign=MARKDOWN_EMAIL_TEST_WITH_SUBJECT>"
            in email_message.body
        )
        assert (
            "This is another link! <https://www.example.com/?utm_source=website&utm_medium=email&utm_campaign=MARKDOWN_EMAIL_TEST_WITH_SUBJECT&foo=bar>"
            in email_message.body
        )

    def test_get_utm_campaign_name(self):
        assert (
            MarkdownEmailTestWithSubject.get_utm_campaign_name()
            == "MARKDOWN_EMAIL_TEST_WITH_SUBJECT"
        )

    def test_get_utm_params(self):
        assert MarkdownEmailTestWithSubject(language="en").get_utm_params() == {
            "utm_campaign": "MARKDOWN_EMAIL_TEST_WITH_SUBJECT",
            "utm_medium": "email",
            "utm_source": "website",
        }

    def test_update_url_params(self, email_message):
        assert (
            email_message.update_url_params(
                "https://localhost:8080/?utm_source=foo",
                utm_source="bar",
                utm_medium="baz",
            )
            == "https://localhost:8080/?utm_source=foo&utm_medium=baz"
        )
        assert (
            email_message.update_url_params(
                "https://localhost:8080", utm_source="bar", utm_medium="baz"
            )
            == "https://localhost:8080?utm_source=bar&utm_medium=baz"
        )

    def test_update_url_params__tracking_uuid(self, email_message):
        email_message._tracking_uuid = "12341234-1234-1234-1234-123412341234"
        assert (
            email_message.update_url_params(
                "https://localhost:8080/?utm_source=foo",
                utm_medium="baz",
            )
            == "http://www.example.com/emark/12341234-1234-1234-1234-123412341234/click?url=https%3A%2F%2Flocalhost%3A8080%2F%3Futm_medium%3Dbaz%26utm_source%3Dfoo"
        )

    @pytest.mark.django_db
    def test_copy(self, email_message):
        clone = copy.copy(email_message)
        assert clone is not email_message
        clone.message()
        email_message.message()
        assert clone.body == email_message.body
