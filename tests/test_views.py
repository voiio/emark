import uuid

import pytest
from django.urls import reverse
from django.utils.http import urlencode
from emark import models
from model_bakery import baker


class TestEmailDetailView:
    @pytest.mark.django_db
    def test_get(self, client):
        msg = baker.make("emark.Send")
        response = client.get(msg.get_absolute_url())
        assert response.status_code == 200
        assert response.content == msg.body.encode("utf-8")
        assert response["Content-Type"] == "text/plain"

    @pytest.mark.django_db
    def test_get__html(self, client):
        msg = baker.make("emark.Send", html="<html></html>")
        response = client.get(msg.get_absolute_url())
        assert response.status_code == 200
        assert response.content == msg.html.encode("utf-8")
        assert response["Content-Type"] == "text/html"

    @pytest.mark.django_db
    def test_get__no_email(self, client):
        response = client.get(
            reverse("emark:email-detail", kwargs={"pk": uuid.uuid4()})
        )
        assert response.status_code == 404


class TestEmailClickView:
    @pytest.mark.django_db
    def test_get__no_redirect_url(self, client, caplog):
        msg = baker.make("emark.Send")
        response = client.get(reverse("emark:email-click", kwargs={"pk": msg.pk}))
        assert response.status_code == 400
        assert response.content == b"Missing url parameter"
        assert "Missing url parameter" in caplog.text

    @pytest.mark.django_db
    def test_get__unsafe_redirect_url(self, client, live_server, caplog):
        msg = baker.make("emark.Send")
        redirect_url = "http://external-domain.com/?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 400
        assert response.content == b"Malformed url parameter"
        assert "Malformed URL parameter" in caplog.text

    @pytest.mark.django_db
    def test_get__different_schema_redirect_url(self, client, live_server):
        msg = baker.make("emark.Send")
        redirect_url = "https://sub.testserver/?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_get__subdomain_redirect_url(self, client, live_server, settings):
        settings.ALLOWED_HOSTS = ["testserver", ".testserver"]
        msg = baker.make("emark.Send")
        redirect_url = "http://sub.testserver/?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_get__absolute_path(self, client, live_server, settings):
        settings.ALLOWED_HOSTS = ["testserver", ".testserver"]
        msg = baker.make("emark.Send")
        redirect_url = "/some/path?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_get__subdomain_debug(self, client, live_server, settings):
        settings.DEBUG = True
        msg = baker.make("emark.Send")
        redirect_url = "http://sub.localhost/?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_get__no_email(self, client):
        response = client.get(reverse("emark:email-click", kwargs={"pk": uuid.uuid4()}))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_get(self, client, live_server):
        msg = baker.make("emark.Send")
        redirect_url = "http://testserver/?utm_source=foo"

        url = reverse("emark:email-click", kwargs={"pk": msg.pk})

        url = f"{url}?{urlencode({'url': redirect_url})}"
        response = client.get(url)
        assert response.status_code == 302
        assert response["Location"] == redirect_url

        email_click = models.Click.objects.get()
        assert email_click.email == msg
        assert email_click.redirect_url == "http://testserver/?utm_source=foo"
        assert email_click.headers == {"Cookie": ""}
        assert email_click.ip_address == "127.0.0.1"
        assert email_click.utm == {}


class TestEmailOpenView:
    @pytest.mark.django_db
    def test_get__no_email(self, client):
        response = client.get(reverse("emark:email-open", kwargs={"pk": uuid.uuid4()}))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_get(self, client):
        msg = baker.make("emark.Send")
        response = client.get(reverse("emark:email-open", kwargs={"pk": msg.pk}))
        assert response.status_code == 200
        assert response.content
        assert response["Content-Type"] == "image/gif"
        assert response["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert response["Content-Length"] == "43"

        email_open = models.Open.objects.get()
        assert email_open.email == msg
        assert email_open.headers == {"Cookie": ""}
        assert email_open.ip_address == "127.0.0.1"
        assert email_open.utm == {}
