from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "content/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Placeholder products until catalog models ship in Phase 2
        context["featured_products"] = [
            {
                "name": "Velvet Rose Lipstick",
                "slug": "velvet-rose-lipstick",
                "price": "1,600",
                "badge": "New",
                "image_alt": "Velvet Rose lipstick product shot",
            },
            {
                "name": "Silk Nude Gloss",
                "slug": "silk-nude-gloss",
                "price": "1,300",
                "badge": "Best seller",
                "image_alt": "Silk Nude gloss product shot",
            },
            {
                "name": "Amber Glow Lip Oil",
                "slug": "amber-glow-lip-oil",
                "price": "1,900",
                "badge": "Trending",
                "image_alt": "Amber Glow lip oil product shot",
            },
            {
                "name": "Evening Edit Bundle",
                "slug": "evening-edit-bundle",
                "price": "4,200",
                "badge": "Bundle",
                "image_alt": "Evening Edit beauty bundle",
            },
        ]
        return context
