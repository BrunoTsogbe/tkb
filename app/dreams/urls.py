"""Routes des rêves."""

from django.urls import path

from . import views

app_name = "dreams"

urlpatterns = [
    path("", views.record, name="record"),
    path("dreams/", views.create, name="create"),
    path("dreams/<uuid:pk>/", views.detail, name="detail"),
]
