from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("faq/", views.FAQListView.as_view(), name="faq"),
    path("contact/", views.contact, name="contact"),
    path("blog/", views.BlogListView.as_view(), name="blog"),
    path("blog/<slug:slug>/", views.BlogDetailView.as_view(), name="blog_detail"),
    path("pages/<slug:slug>/", views.SitePageDetailView.as_view(), name="page"),
    path("newsletter/", views.newsletter_subscribe, name="newsletter"),
    path("gift-cards/", views.gift_cards, name="gift_cards"),
]
