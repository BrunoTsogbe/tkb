"""Routes des rêves (specifications_architecture.pdf §4.4)."""

from django.urls import path

from . import views

app_name = "dreams"

urlpatterns = [
    path("", views.record, name="record"),
    path("dreams/", views.collection, name="collection"),
    path("dreams/<uuid:pk>/", views.detail, name="detail"),
    path("dreams/<uuid:pk>/status/", views.status, name="status"),
    path("dreams/<uuid:pk>/edit/", views.edit, name="edit"),
    path("dreams/<uuid:pk>/retry/", views.retry, name="retry"),
    path("dreams/<uuid:pk>/image/", views.image, name="image"),
    path("dreams/<uuid:pk>/delete/", views.delete, name="delete"),
]
