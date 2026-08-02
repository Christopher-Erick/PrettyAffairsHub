from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("password-reset/", views.UserPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("profile/", views.profile, name="profile"),
    path("addresses/new/", views.address_create, name="address_create"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/<slug:slug>/", views.wishlist_toggle, name="wishlist_toggle"),
]
