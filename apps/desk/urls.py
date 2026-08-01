from django.urls import path

from apps.desk import views

app_name = "desk"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/variants/add/", views.variant_add, name="variant_add"),
    path("products/<int:pk>/variants/<int:variant_id>/delete/", views.variant_delete, name="variant_delete"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("content/", views.content_hub, name="content_hub"),
    path("content/sections/", views.section_list, name="section_list"),
    path("content/sections/new/", views.section_create, name="section_create"),
    path("content/sections/<int:pk>/", views.section_edit, name="section_edit"),
    path("content/journal/", views.blog_list, name="blog_list"),
    path("content/journal/new/", views.blog_create, name="blog_create"),
    path("content/journal/<int:pk>/", views.blog_edit, name="blog_edit"),
    path("content/faqs/", views.faq_list, name="faq_list"),
    path("content/faqs/new/", views.faq_create, name="faq_create"),
    path("content/faqs/<int:pk>/", views.faq_edit, name="faq_edit"),
    path("content/quotes/", views.testimonial_list, name="testimonial_list"),
    path("content/quotes/new/", views.testimonial_create, name="testimonial_create"),
    path("content/quotes/<int:pk>/", views.testimonial_edit, name="testimonial_edit"),
    path("content/pages/", views.page_list, name="page_list"),
    path("content/pages/new/", views.page_create, name="page_create"),
    path("content/pages/<int:pk>/", views.page_edit, name="page_edit"),
    path("content/flash-sales/", views.flash_list, name="flash_list"),
    path("content/flash-sales/new/", views.flash_create, name="flash_create"),
    path("content/flash-sales/<int:pk>/", views.flash_edit, name="flash_edit"),
    path("messages/", views.message_list, name="message_list"),
    path("messages/<int:pk>/", views.message_detail, name="message_detail"),
]
