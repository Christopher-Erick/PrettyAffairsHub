import re

from django import forms


KENYA_CITIES = [
    ("Nairobi", "Nairobi"),
    ("Mombasa", "Mombasa"),
    ("Kisumu", "Kisumu"),
    ("Nakuru", "Nakuru"),
    ("Eldoret", "Eldoret"),
    ("Other", "Other Kenya city"),
]

# Kenya mobiles: 07XXXXXXXX, 01XXXXXXXX, +2547XXXXXXXX, 2547XXXXXXXX
_PHONE_RE = re.compile(
    r"^(?:\+?254|0)(?:7\d{8}|1\d{8})$"
)


class CheckoutForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "field", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Phone",
        widget=forms.TextInput(
            attrs={
                "class": "field",
                "placeholder": "07XX XXX XXX",
                "autocomplete": "tel",
                "inputmode": "tel",
            }
        ),
    )
    shipping_name = forms.CharField(
        label="Full name",
        widget=forms.TextInput(
            attrs={"class": "field", "autocomplete": "name", "placeholder": "Who should receive the order?"}
        ),
    )
    shipping_line1 = forms.CharField(
        label="Address",
        widget=forms.TextInput(
            attrs={"class": "field", "autocomplete": "street-address", "placeholder": "Street, building, or house"}
        ),
    )
    shipping_city = forms.ChoiceField(
        label="Shipping city",
        choices=KENYA_CITIES,
        widget=forms.Select(attrs={"class": "field", "data-city-select": True}),
    )
    shipping_location = forms.CharField(
        label="Shipping location",
        widget=forms.TextInput(
            attrs={
                "class": "field",
                "placeholder": "Estate, area, or landmark (e.g. Westlands, Kilimani)",
            }
        ),
    )
    notes = forms.CharField(
        label="Delivery note",
        widget=forms.Textarea(
            attrs={
                "class": "field",
                "rows": 2,
                "placeholder": "Gate code, floor, preferred time…",
            }
        ),
    )
    coupon_code = forms.CharField(
        required=False,
        label="Coupon code",
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "Optional"}),
    )

    def clean_shipping_city(self):
        city = self.cleaned_data["shipping_city"]
        return city if city != "Other" else "Other"

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        digits = re.sub(r"[\s\-()]", "", raw)
        if not _PHONE_RE.match(digits):
            raise forms.ValidationError(
                "Enter a valid Kenya phone number (e.g. 07XX XXX XXX or +2547XX XXX XXX)."
            )
        if digits.startswith("+"):
            return digits
        if digits.startswith("254"):
            return f"+{digits}"
        if digits.startswith("0"):
            return f"+254{digits[1:]}"
        return digits

    def clean(self):
        cleaned = super().clean()
        # Map UI “shipping location” into the stored address line 2.
        location = (cleaned.get("shipping_location") or "").strip()
        cleaned["shipping_line2"] = location
        cleaned["shipping_county"] = ""
        cleaned["shipping_postal_code"] = ""
        cleaned["shipping_country"] = "Kenya"
        cleaned["is_gift"] = False
        cleaned["gift_note"] = ""
        for required in (
            "email",
            "phone",
            "shipping_name",
            "shipping_line1",
            "shipping_city",
            "shipping_location",
            "notes",
        ):
            if required in cleaned and not str(cleaned.get(required) or "").strip():
                self.add_error(required, "This field is required.")
        return cleaned
