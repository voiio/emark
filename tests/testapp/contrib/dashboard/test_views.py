import pytest
from django.http import Http404
from emark.contrib.dashboard import _registry, views
from emark.message import MarkdownEmail


class MarkdownEmailTest(MarkdownEmail):
    template = "template.md"


def test_serialize_email_class():
    assert views.serialize_email_class(email_class=MarkdownEmailTest, path="path") == {
        "app_label": "tests",
        "class": MarkdownEmailTest,
        "detail_url": "/emark/dashboard/path/preview",
        "doc": "",
        "name": "MarkdownEmailTest",
        "preview": MarkdownEmailTest.render_preview,
    }


class TestDashboardView:

    def test_get_context_data(self, rf):
        request = rf.get("/emark/dashboard/")
        view = views.DashboardView()
        view.setup(request)
        context = view.get_context_data()
        assert context == {
            "site_header": "eMark",
            "site_title": "eMark",
            "title": "Dashboard",
            "emails": [],
            "view": view,
        }

    def test_render(self, admin_client):
        response = admin_client.get("/emark/dashboard/")
        assert response.status_code == 200


class TestEmailPreviewView:

    def test_dispatch__404(self, rf):
        request = rf.get("/emark/dashboard/path/preview")
        view = views.EmailPreviewView()
        with pytest.raises(Http404):
            view.dispatch(request, email_class="path")

    def test_dispatch(self, rf):
        view = views.EmailPreviewView()
        view.request = rf.get("/emark/dashboard/tests.MarkdownEmailTest/preview")
        view.kwargs = {"email_class": "tests.MarkdownEmailTest"}
        _registry["MarkdownEmailTest"] = MarkdownEmailTest
        view.dispatch(view.request, email_class="MarkdownEmailTest")
        assert view.email_class == MarkdownEmailTest
        del _registry["MarkdownEmailTest"]

    def test_get_context_data(self):
        view = views.EmailPreviewView()
        view.kwargs = {"email_class": "MarkdownEmailTest"}
        view.email_class = MarkdownEmailTest
        context = view.get_context_data()
        _registry["MarkdownEmailTest"] = MarkdownEmailTest
        assert context == {
            "view": view,
            "site_header": "eMark",
            "site_title": "eMark",
            "title": "Dashboard",
            "subtitle": "MarkdownEmailTest",
            "email": {
                "app_label": "tests",
                "class": MarkdownEmailTest,
                "name": "MarkdownEmailTest",
                "doc": "",
                "detail_url": "/emark/dashboard/MarkdownEmailTest/preview",
                "preview": MarkdownEmailTest.render_preview,
            },
        }

        del _registry["MarkdownEmailTest"]

    def test_render(self, admin_client):
        _registry["MarkdownEmailTest"] = MarkdownEmailTest
        response = admin_client.get("/emark/dashboard/MarkdownEmailTest/preview")
        assert response.status_code == 200
        del _registry["MarkdownEmailTest"]
