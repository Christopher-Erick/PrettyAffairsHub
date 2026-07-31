from django.urls import path

from .views import ShopComingSoonView

app_name = "catalog"

urlpatterns = [
    path("", ShopComingSoonView.as_view(), name="shop"),
]
