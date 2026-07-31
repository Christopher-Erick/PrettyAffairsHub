from django.contrib.sitemaps import Sitemap

from apps.catalog.models import Category, Collection, Product
from apps.content.models import BlogPost, SitePage


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.published()


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)


class CollectionSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Collection.objects.filter(is_active=True)


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return BlogPost.objects.filter(is_published=True)


class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return SitePage.objects.filter(is_published=True)


sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "collections": CollectionSitemap,
    "blog": BlogSitemap,
    "pages": PageSitemap,
}
