from django.views.generic import TemplateView


class ShopComingSoonView(TemplateView):
    template_name = "catalog/shop.html"
