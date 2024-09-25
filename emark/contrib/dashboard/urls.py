from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path

from . import views

app_name = "emark-dashboard"

urlpatterns = [
    path("", staff_member_required(views.DashboardView.as_view()), name="dashboard"),
    path(
        "<str:email_class>/",
        include(
            [
                path(
                    "preview",
                    staff_member_required(views.EmailPreviewView.as_view()),
                    name="email-preview",
                )
            ]
        ),
    ),
]
