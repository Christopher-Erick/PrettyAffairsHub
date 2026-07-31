from django import forms


KENYA_CITIES = [
    ("Nairobi", "Nairobi"),
    ("Mombasa", "Mombasa"),
    ("Kisumu", "Kisumu"),
    ("Nakuru", "Nakuru"),
    ("Eldoret", "Eldoret"),
    ("Other", "Other Kenya city"),
]


class CheckoutForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "field"}))
    phone = forms.CharField(
        required=False,
        label="Phone (M-Pesa / delivery)",
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "07XX XXX XXX"}),
    )
    shipping_name = forms.CharField(widget=forms.TextInput(attrs={"class": "field"}))
    shipping_line1 = forms.CharField(label="Address", widget=forms.TextInput(attrs={"class": "field"}))
    shipping_line2 = forms.CharField(
        required=False, label="Apartment, suite, etc.", widget=forms.TextInput(attrs={"class": "field"})
    )
    shipping_city = forms.ChoiceField(
        choices=KENYA_CITIES,
        widget=forms.Select(attrs={"class": "field", "data-city-select": True}),
    )
    shipping_county = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    shipping_postal_code = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    shipping_country = forms.CharField(
        initial="Kenya", widget=forms.TextInput(attrs={"class": "field", "readonly": True})
    )
    coupon_code = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    notes = forms.CharField(
        required=False,
        label="Delivery notes",
        widget=forms.Textarea(attrs={"class": "field", "rows": 2, "placeholder": "Gate code, landmark…"}),
    )
    is_gift = forms.BooleanField(
        required=False,
        label="This order is a gift",
        widget=forms.CheckboxInput(attrs={"data-gift-toggle": True}),
    )
    gift_note = forms.CharField(
        required=False,
        label="Gift message",
        max_length=280,
        widget=forms.Textarea(
            attrs={
                "class": "field",
                "rows": 3,
                "data-gift-input": True,
                "placeholder": "Write a short note for the recipient…",
                "maxlength": "280",
            }
        ),
    )

    def clean_shipping_city(self):
        city = self.cleaned_data["shipping_city"]
        return city if city != "Other" else "Other"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_gift") and not (cleaned.get("gift_note") or "").strip():
            self.add_error("gift_note", "Add a short gift message, or uncheck gift.")
        return cleaned
