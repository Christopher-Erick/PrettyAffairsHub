from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<str:order_number>/", views.order_confirmation, name="confirmation"),
    path("history/", views.order_history, name="history"),
    path("history/<str:order_number>/", views.order_detail, name="detail"),
    path("track/", views.track_order, name="track"),
]
