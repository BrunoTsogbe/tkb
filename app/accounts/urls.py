"""Routes des comptes."""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import AsyncPasswordResetForm

app_name = "accounts"

urlpatterns = [
    path("", views.account, name="account"),
    path("export/", views.export, name="export"),
    path("delete/", views.delete_account, name="delete"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=AsyncPasswordResetForm,
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("signup/", views.signup, name="signup"),
    path("login/", views.RateLimitedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("consent/", views.consent, name="consent"),
]
