from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="shop"),
    path("bundles/", views.BundleListView.as_view(), name="bundles"),
    path("bundles/<slug:slug>/", views.BundleDetailView.as_view(), name="bundle_detail"),
    path("category/<slug:slug>/", views.CategoryDetailView.as_view(), name="category"),
    path("collection/<slug:slug>/", views.CollectionDetailView.as_view(), name="collection"),
    path("product/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("product/<slug:slug>/review/", views.submit_review, name="submit_review"),
]
