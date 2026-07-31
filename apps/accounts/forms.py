from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, CustomerProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "field", "autocomplete": "username"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "field", "autocomplete": "current-password"})
    )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "field"}))

    class Meta:
        model = CustomerProfile
        fields = ("phone",)
        widgets = {"phone": forms.TextInput(attrs={"class": "field"})}


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "county",
            "postal_code",
            "country",
            "is_default",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "field"}),
            "phone": forms.TextInput(attrs={"class": "field"}),
            "line1": forms.TextInput(attrs={"class": "field"}),
            "line2": forms.TextInput(attrs={"class": "field"}),
            "city": forms.TextInput(attrs={"class": "field"}),
            "county": forms.TextInput(attrs={"class": "field"}),
            "postal_code": forms.TextInput(attrs={"class": "field"}),
            "country": forms.TextInput(attrs={"class": "field"}),
        }
