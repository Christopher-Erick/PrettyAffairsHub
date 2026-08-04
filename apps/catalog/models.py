from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Brand(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", kwargs={"slug": self.slug})

    def descendant_ids(self):
        """Return this category id plus all nested child ids."""
        ids = [self.id]
        children = list(self.children.filter(is_active=True))
        while children:
            next_level = []
            for child in children:
                ids.append(child.id)
                next_level.extend(list(child.children.filter(is_active=True)))
            children = next_level
        return ids

    @classmethod
    def tree_for_filters(cls):
        parents = (
            cls.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related(
                models.Prefetch(
                    "children",
                    queryset=cls.objects.filter(is_active=True).order_by("sort_order", "name"),
                )
            )
            .order_by("sort_order", "name")
        )
        return parents


class Collection(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:collection", kwargs={"slug": self.slug})


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.published().filter(is_featured=True)

    def new_arrivals(self):
        return self.published().filter(is_new=True)

    def best_sellers(self):
        return self.published().filter(is_bestseller=True)

    def trending(self):
        return self.published().filter(is_trending=True)


class Product(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.ForeignKey(
        Brand, null=True, blank=True, related_name="products", on_delete=models.SET_NULL
    )
    categories = models.ManyToManyField(Category, blank=True, related_name="products")
    collections = models.ManyToManyField(Collection, blank=True, related_name="products")
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    benefits = models.TextField(blank=True, help_text="One benefit per line")
    ingredients = models.TextField(blank=True)
    directions = models.TextField(blank=True)
    specifications = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    source_name = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_limited_offer = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    def _variant_list(self):
        """Prefer prefetched variants to avoid N+1 on product cards."""
        return list(self.variants.all())

    @property
    def in_stock(self):
        variants = self._variant_list()
        if variants:
            return any(v.is_active and v.stock > 0 for v in variants)
        return self.stock > 0

    @property
    def available_stock(self):
        variants = [v for v in self._variant_list() if v.is_active]
        if variants:
            return sum(v.stock for v in variants)
        return self.stock

    @property
    def is_low_stock(self):
        stock = self.available_stock
        if stock < 1:
            return False
        return stock <= 8

    @property
    def default_variant(self):
        for variant in self._variant_list():
            if variant.is_active and variant.stock > 0:
                return variant
        return None

    @property
    def effective_price(self):
        return self.price

    @property
    def on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def primary_image(self):
        # Iterate prefetched images (Meta ordering) instead of a fresh ORDER BY query.
        for image in self.images.all():
            return image
        return None

    def benefit_list(self):
        return [line.strip() for line in self.benefits.splitlines() if line.strip()]

    @property
    def card_tagline(self):
        benefits = self.benefit_list()
        if benefits:
            return " • ".join(benefits[:3])
        return self.short_description


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.name} image"


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, blank=True)
    color_hex = models.CharField(
        max_length=7,
        blank=True,
        help_text="Shade swatch as a hex colour, e.g. #A94F5C",
    )
    image = models.ImageField(upload_to="products/variants/%Y/%m/", blank=True)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        unique_together = [("product", "name")]

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.product.price


class ProductRelation(TimeStampedModel):
    RELATION_SIMILAR = "similar"
    RELATION_FBT = "fbt"
    RELATION_CHOICES = [
        (RELATION_SIMILAR, "Similar products"),
        (RELATION_FBT, "Frequently bought together"),
    ]

    from_product = models.ForeignKey(
        Product, related_name="relations_from", on_delete=models.CASCADE
    )
    to_product = models.ForeignKey(
        Product, related_name="relations_to", on_delete=models.CASCADE
    )
    relation_type = models.CharField(max_length=20, choices=RELATION_CHOICES)

    class Meta:
        unique_together = [("from_product", "to_product", "relation_type")]

    def __str__(self):
        return f"{self.from_product} → {self.to_product} ({self.relation_type})"


class Bundle(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, through="BundleItem", related_name="bundles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:bundle_detail", kwargs={"slug": self.slug})

    @property
    def has_full_trio(self):
        return self.items.count() == 3


class BundleItem(models.Model):
    bundle = models.ForeignKey(Bundle, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("bundle", "product")]

    def __str__(self):
        return f"{self.bundle.name}: {self.product.name} x{self.quantity}"
