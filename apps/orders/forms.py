from django import forms


class CheckoutForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "field"}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    shipping_name = forms.CharField(widget=forms.TextInput(attrs={"class": "field"}))
    shipping_line1 = forms.CharField(label="Address", widget=forms.TextInput(attrs={"class": "field"}))
    shipping_line2 = forms.CharField(
        required=False, label="Apartment, suite, etc.", widget=forms.TextInput(attrs={"class": "field"})
    )
    shipping_city = forms.CharField(widget=forms.TextInput(attrs={"class": "field"}))
    shipping_county = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    shipping_postal_code = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    shipping_country = forms.CharField(
        initial="Kenya", widget=forms.TextInput(attrs={"class": "field"})
    )
    coupon_code = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "field", "rows": 3}))
