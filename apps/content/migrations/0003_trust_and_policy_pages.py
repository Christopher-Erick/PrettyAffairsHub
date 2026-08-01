"""Seed trust/policy CMS content used across About, FAQ, and legal pages."""

from django.db import migrations


ABOUT_BODY = """Pretty Affairs Hub is a Kenya-based beauty destination built for everyday elegance.

We curate colour, skin-kind formulas, and finishing pieces — from prestige lip favourites to our own Pretty Affairs body and hand care — so your ritual feels refined without the noise.

Every order is packed with care. We favour clear shade guidance, honest stock cues, and delivery that respects your time. Whether you are building a soft nude edit or a bold weekend look, we are here to help you choose with confidence.

Questions before you buy? Message us on WhatsApp or use the contact form — a real person replies."""


POLICIES = (
    (
        "privacy",
        "Privacy policy",
        """We respect your privacy.

What we collect
We collect information you give us when you create an account, place an order, subscribe to the newsletter, or send a message — such as your name, email, phone, delivery address, and order details.

How we use it
We use your details to fulfil orders, confirm delivery, respond to enquiries, improve the shop, and (only if you subscribe) send newsletters. We do not sell your personal information.

Sharing
We share data only with service partners needed to run the shop (for example payment confirmation helpers, delivery partners, and hosting). They may only use your data for that purpose.

Security
We protect your data with HTTPS, secure cookies, and access limited to store staff. No method of transmission is 100% secure, but we take reasonable precautions.

Your choices
You may request a copy of your data, ask us to update it, or unsubscribe from marketing at any time via the contact form or WhatsApp.

Contact
For privacy questions, email or message us through the Contact page.""",
    ),
    (
        "terms",
        "Terms of service",
        """By shopping at Pretty Affairs Hub you agree to these terms.

Orders
Placing an order is an offer to buy. We confirm acceptance by email or WhatsApp. Prices are in Kenyan Shillings (KSh) unless stated otherwise. We may cancel an order if an item is unavailable or if payment cannot be verified.

Accounts
You are responsible for keeping your login details safe. Store staff accounts are for running the shop only.

Products
Product photos and shade names are guides. Screens and lighting can shift colour slightly. Check shade notes on the product page when choosing.

Acceptable use
Do not misuse the site, attempt unauthorised access, or submit abusive content in reviews or messages.

Changes
We may update these terms; the version on this page is the current one. Continued use of the site means you accept the updated terms.""",
    ),
    (
        "shipping",
        "Shipping & delivery",
        """We deliver across Kenya.

Free delivery
Orders of KSh 5,000 and above qualify for free delivery. Below that threshold, a flat delivery fee of KSh 300 applies at checkout (unless a campaign states otherwise).

Timing
Nairobi and nearby areas usually arrive within 1–3 business days after payment is confirmed. Other towns typically take 2–5 business days. You will receive tracking details when your order ships.

Payment confirmation
Orders stay pending until we confirm payment (for example M-Pesa). Dispatch starts after confirmation.

Issues
If a parcel is delayed or arrives damaged, contact us with your order number within 48 hours of delivery so we can help.""",
    ),
    (
        "returns",
        "Returns & exchanges",
        """We want you to love what you order.

Hygiene & beauty
For health and safety, opened cosmetics, lip products, and personal-care items cannot be returned once the seal is broken — unless the item arrived damaged or incorrect.

Eligible returns
Unopened items in original packaging may be returned within 7 days of delivery if they are unused and the seal is intact. Please include your order number.

Exchanges
Subject to stock, we can exchange an unopened shade or size. Message us on WhatsApp or Contact with your order number and the product you prefer.

Damaged or wrong item
If something arrives damaged or wrong, send a photo and your order number within 48 hours. We will replace it or arrange a refund of the item price.

Refunds
Approved refunds are processed to the original payment method or as store credit, usually within 5–10 business days after we receive and inspect the return.""",
    ),
)


FAQS = (
    (
        "How long does delivery take?",
        "Nairobi and nearby areas usually take 1–3 business days after payment is confirmed. Other Kenyan towns typically take 2–5 business days. Free delivery applies on orders of KSh 5,000 and above.",
        10,
    ),
    (
        "Do you accept M-Pesa?",
        "Yes. After you place an order we confirm payment (including M-Pesa) before packing. Keep your order number handy when you message us.",
        20,
    ),
    (
        "Can I return a lipstick or lip oil?",
        "Opened beauty products cannot be returned for hygiene reasons. Unopened, sealed items may be returned within 7 days. Damaged or wrong items are replaced — see our Returns page.",
        30,
    ),
    (
        "How do I track my order?",
        "Use Track order in the footer with your order number and the email you used at checkout. We also share updates by email or WhatsApp when your parcel ships.",
        40,
    ),
    (
        "Are the shade swatches accurate?",
        "Swatches help you preview colour on screen. Real life can vary slightly with lighting and undertone — check the product notes and message us on WhatsApp if you need a match tip.",
        50,
    ),
    (
        "Do you sell gift cards?",
        "Yes. Visit Gift cards for denominations. We arrange fulfilment over WhatsApp after you choose an amount.",
        60,
    ),
)


TESTIMONIALS = (
    ("Amina K.", "Packaging feels premium and the shades are stunning. Delivery to Westlands was quick.", 5, 10),
    ("Faith W.", "Checkout was simple and they confirmed my M-Pesa on WhatsApp the same evening.", 5, 20),
    ("Njeri M.", "Finally a Kenyan beauty shop that explains shades properly. The lip oil edit is my go-to.", 5, 30),
    ("Grace O.", "Returned once for a sealed wrong shade — exchange was polite and fast. Will order again.", 5, 40),
)


def forwards(apps, schema_editor):
    SitePage = apps.get_model("content", "SitePage")
    FAQ = apps.get_model("content", "FAQ")
    Testimonial = apps.get_model("content", "Testimonial")

    SitePage.objects.update_or_create(
        slug="about",
        defaults={"title": "About Pretty Affairs Hub", "body": ABOUT_BODY, "is_published": True},
    )
    for slug, title, body in POLICIES:
        SitePage.objects.update_or_create(
            slug=slug,
            defaults={"title": title, "body": body, "is_published": True},
        )

    for question, answer, sort_order in FAQS:
        FAQ.objects.update_or_create(
            question=question,
            defaults={"answer": answer, "sort_order": sort_order, "is_active": True},
        )

    for author_name, quote, rating, sort_order in TESTIMONIALS:
        Testimonial.objects.update_or_create(
            author_name=author_name,
            defaults={
                "quote": quote,
                "rating": rating,
                "sort_order": sort_order,
                "is_featured": True,
            },
        )

    try:
        from apps.core.smart_cache import invalidate_catalog_cache

        invalidate_catalog_cache(reason="trust and policy pages seeded")
    except Exception:
        pass


def backwards(apps, schema_editor):
    SitePage = apps.get_model("content", "SitePage")
    FAQ = apps.get_model("content", "FAQ")
    Testimonial = apps.get_model("content", "Testimonial")
    SitePage.objects.filter(slug__in=["privacy", "terms", "shipping", "returns"]).delete()
    FAQ.objects.filter(question__in=[q for q, _, _ in FAQS]).delete()
    Testimonial.objects.filter(author_name__in=[t[0] for t in TESTIMONIALS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_sitepage_ordering"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
