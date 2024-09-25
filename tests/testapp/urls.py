from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(
        "emark/",
        include(
            [
                path("", include("emark.urls")),
                path("dashboard/", include("emark.contrib.dashboard.urls")),
            ]
        ),
    ),
    path("admin/", admin.site.urls),
]
