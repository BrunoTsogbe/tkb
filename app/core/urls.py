"""Routes transverses."""

from django.urls import path

from . import views

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("supervision/", views.supervision, name="supervision"),
]
