from django.urls import path

from . import views

app_name = "emark"
urlpatterns = [
    path("<uuid:pk>/", views.EmailDetailView.as_view(), name="email-detail"),
    path("<uuid:pk>/click", views.EmailClickView.as_view(), name="email-click"),
    path("<uuid:pk>/open", views.EmailOpenView.as_view(), name="email-open"),
]
