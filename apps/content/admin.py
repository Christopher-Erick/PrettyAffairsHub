from django.contrib import admin

from .models import (
    BlogPost,
    ContactMessage,
    FAQ,
    HomepageSection,
    NewsletterSubscriber,
    SitePage,
    Testimonial,
)


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_tutorial", "is_published", "published_at")
    list_filter = ("is_tutorial", "is_published")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "excerpt")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "rating", "is_featured", "sort_order")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_handled", "replied_at", "created_at")
    list_filter = ("is_handled",)
    readonly_fields = ("replied_at", "replied_by", "created_at")
    search_fields = ("name", "email", "subject", "message", "reply_body")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    search_fields = ("email",)


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    prepopulated_fields = {"slug": ("title",)}
